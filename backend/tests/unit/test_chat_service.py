"""Unit test for ChatService.answer with conversation memory (fakes, no DB)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest

from app.domains.chat.models.conversation import Conversation, Message
from app.domains.chat.schemas import ChatRequest
from app.domains.chat.services.chat_service import ChatService
from app.domains.retrieval.schemas import RetrievedChunk
from app.domains.retrieval.services.retrieval_service import RetrievalService
from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.reranker.base import NullReranker


class _FakeSession:
    async def flush(self) -> None: ...
    async def commit(self) -> None: ...


class _FakeConvRepo:
    async def touch(self, conversation: Conversation) -> None: ...


class _FakeMsgRepo:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    async def add(self, message: Message) -> Message:
        if message.id is None:
            message.id = uuid.uuid4()
        self.messages.append(message)
        return message

    async def recent(self, conversation_id: uuid.UUID, limit: int = 10) -> Sequence[Message]:
        return self.messages[-limit:]

    async def list_for_conversation(self, conversation_id: uuid.UUID, limit: int = 50) -> Sequence[Message]:
        return self.messages


class _FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks

    async def retrieve(self, **_: object) -> list[RetrievedChunk]:
        return list(self._chunks)


@pytest.mark.asyncio
async def test_chat_answer_grounds_and_persists_messages() -> None:
    chunks = [RetrievedChunk(uuid.uuid4(), uuid.uuid4(), "Paris is the capital of France.", 1.0, "dense")]
    retrieval = RetrievalService(_FakeRetriever(chunks), _FakeRetriever(chunks), NullReranker())
    msg_repo = _FakeMsgRepo()
    service = ChatService(_FakeSession(), _FakeConvRepo(), msg_repo, retrieval, FakeLLMProvider())

    conversation = Conversation(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        workspace_id=None,
        title="t",
        system_prompt=None,
    )

    resp = await service.answer(
        conversation=conversation, user_id=conversation.user_id, req=ChatRequest(query="Capital of France?")
    )

    assert "[1]" in resp.answer
    assert resp.citations and resp.citations[0].marker == 1
    assert resp.model == "fake-llm"
    # user message + assistant message persisted
    roles = [m.role for m in msg_repo.messages]
    assert roles == ["user", "assistant"]
    assert msg_repo.messages[-1].citations  # assistant message carries citations
