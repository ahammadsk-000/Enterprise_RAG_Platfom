"""Chat service: conversation management + grounded answers with memory.

Reuses the retrieval engine + citation engine from Phase 4 and adds conversation
memory (recent message history injected into the prompt). Exposes a non-streaming
`answer` and a streaming `stream_answer` async generator for the WebSocket.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domains.chat.models.conversation import Conversation, Message
from app.domains.chat.repositories.conversation_repository import (
    ConversationRepository,
    MessageRepository,
)
from app.domains.chat.schemas import ChatRequest, ChatResponse, ConversationCreate
from app.domains.rag.citations import build_citations, confidence_score
from app.domains.rag.prompts import SYSTEM_PROMPT, build_context
from app.domains.retrieval.compression import compress
from app.domains.retrieval.schemas import RetrievedChunk
from app.domains.retrieval.services.retrieval_service import RetrievalService
from app.integrations.llm.base import ChatMessage, LLMProvider

logger = get_logger(__name__)

_HISTORY_TURNS = 8
_MAX_CONTEXT_TOKENS = 3000
_DEFAULT_TITLE = "New conversation"
_TITLE_MAX = 60
_NO_CONTEXT = (
    "I couldn't find anything relevant to that in your documents. Try rephrasing, "
    "or make sure the source is uploaded and indexed."
)


class ChatService:
    def __init__(
        self,
        session: AsyncSession,
        conversations: ConversationRepository,
        messages: MessageRepository,
        retrieval: RetrievalService,
        llm: LLMProvider,
    ) -> None:
        self._session = session
        self._conversations = conversations
        self._messages = messages
        self._retrieval = retrieval
        self._llm = llm

    # ── conversation CRUD ─────────────────────────────────────────────────────
    async def create_conversation(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, data: ConversationCreate
    ) -> Conversation:
        conversation = await self._conversations.add(
            Conversation(
                organization_id=organization_id,
                user_id=user_id,
                workspace_id=data.workspace_id,
                title=data.title,
                system_prompt=data.system_prompt,
            )
        )
        await self._session.commit()
        return conversation

    async def list_conversations(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> Sequence[Conversation]:
        return await self._conversations.list_for_user(organization_id, user_id)

    async def get_conversation(self, conversation_id: uuid.UUID, organization_id: uuid.UUID) -> Conversation:
        conversation = await self._conversations.get(conversation_id)
        if conversation is None or conversation.organization_id != organization_id:
            raise NotFoundError("Conversation not found.")
        return conversation

    async def list_messages(self, conversation_id: uuid.UUID, organization_id: uuid.UUID) -> Sequence[Message]:
        await self.get_conversation(conversation_id, organization_id)
        return await self._messages.list_for_conversation(conversation_id)

    async def rename_conversation(
        self, conversation_id: uuid.UUID, organization_id: uuid.UUID, user_id: uuid.UUID, title: str
    ) -> Conversation:
        conversation = await self._owned_conversation(conversation_id, organization_id, user_id)
        conversation.title = title.strip()[:_TITLE_MAX] or _DEFAULT_TITLE
        await self._session.commit()
        return conversation

    async def delete_conversation(
        self, conversation_id: uuid.UUID, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        conversation = await self._owned_conversation(conversation_id, organization_id, user_id)
        await self._conversations.delete(conversation)
        await self._session.commit()

    async def _owned_conversation(
        self, conversation_id: uuid.UUID, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation:
        conversation = await self.get_conversation(conversation_id, organization_id)
        if conversation.user_id != user_id:
            raise NotFoundError("Conversation not found.")
        return conversation

    # ── answering ─────────────────────────────────────────────────────────────
    async def answer(
        self, *, conversation: Conversation, user_id: uuid.UUID, req: ChatRequest
    ) -> ChatResponse:
        start = time.perf_counter()
        history, context = await self._prepare(conversation, user_id, req)

        if not context:
            assistant, latency_ms = await self._finalize_no_context(conversation, start)
            return ChatResponse(
                message_id=assistant.id, answer=_NO_CONTEXT, citations=[], confidence=0.0,
                model=self._llm.model_name, prompt_tokens=0, completion_tokens=0, latency_ms=latency_ms,
            )

        messages = self._build_messages(conversation, history, context, req.query)
        result = await self._llm.generate(messages, temperature=req.temperature)
        citations = build_citations(result.text, context)
        confidence = confidence_score(result.text, context, citations)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        assistant = await self._persist_assistant(
            conversation, result.text, result.model_dump() if hasattr(result, "model_dump") else None,
            citations, confidence, result.prompt_tokens, result.completion_tokens, latency_ms,
        )
        await self._conversations.touch(conversation)
        await self._session.commit()

        return ChatResponse(
            message_id=assistant.id,
            answer=result.text,
            citations=citations,
            confidence=confidence,
            model=self._llm.model_name,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=latency_ms,
        )

    async def stream_answer(
        self, *, conversation: Conversation, user_id: uuid.UUID, req: ChatRequest
    ) -> AsyncIterator[dict]:
        start = time.perf_counter()
        history, context = await self._prepare(conversation, user_id, req)

        if not context:
            assistant, latency_ms = await self._finalize_no_context(conversation, start)
            yield {"type": "token", "content": _NO_CONTEXT}
            yield {
                "type": "done", "message_id": str(assistant.id), "citations": [],
                "confidence": 0.0, "model": self._llm.model_name, "latency_ms": latency_ms,
            }
            return

        messages = self._build_messages(conversation, history, context, req.query)
        buffer: list[str] = []
        async for token in self._llm.stream(messages, temperature=req.temperature):
            buffer.append(token)
            yield {"type": "token", "content": token}

        text = "".join(buffer)
        citations = build_citations(text, context)
        confidence = confidence_score(text, context, citations)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        assistant = await self._persist_assistant(
            conversation, text, None, citations, confidence, 0, len(text.split()), latency_ms
        )
        await self._conversations.touch(conversation)
        await self._session.commit()

        yield {
            "type": "done",
            "message_id": str(assistant.id),
            "citations": [c.model_dump(mode="json") for c in citations],
            "confidence": confidence,
            "model": self._llm.model_name,
            "latency_ms": latency_ms,
        }

    # ── internals ─────────────────────────────────────────────────────────────
    async def _finalize_no_context(
        self, conversation: Conversation, start: float
    ) -> tuple[Message, float]:
        """Persist a grounded 'no relevant sources' answer (skips the LLM)."""
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        assistant = await self._persist_assistant(
            conversation, _NO_CONTEXT, None, [], 0.0, 0, len(_NO_CONTEXT.split()), latency_ms
        )
        await self._conversations.touch(conversation)
        await self._session.commit()
        return assistant, latency_ms

    async def _prepare(
        self, conversation: Conversation, user_id: uuid.UUID, req: ChatRequest
    ) -> tuple[Sequence[Message], list[RetrievedChunk]]:
        history = await self._messages.recent(conversation.id, _HISTORY_TURNS)
        # Auto-title the conversation from its first question.
        if conversation.title in (None, "", _DEFAULT_TITLE) and not any(m.role == "user" for m in history):
            title = " ".join(req.query.split())[:_TITLE_MAX]
            conversation.title = title + ("…" if len(req.query.strip()) > _TITLE_MAX else "")
        await self._messages.add(
            Message(conversation_id=conversation.id, role="user", content=req.query)
        )
        retrieved, _ = await self._retrieval.search(
            organization_id=conversation.organization_id,
            workspace_id=conversation.workspace_id,
            query=req.query,
            top_k=req.top_k,
            strategy=req.strategy,
            rerank=req.rerank,
            user_id=user_id,
        )
        return history, compress(retrieved, max_tokens=_MAX_CONTEXT_TOKENS)

    def _build_messages(
        self,
        conversation: Conversation,
        history: Sequence[Message],
        context: list[RetrievedChunk],
        question: str,
    ) -> list[ChatMessage]:
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=conversation.system_prompt or SYSTEM_PROMPT)
        ]
        for msg in history:
            if msg.role in ("user", "assistant"):
                messages.append(ChatMessage(role=msg.role, content=msg.content))  # type: ignore[arg-type]
        sources = build_context(context) or "(no sources found)"
        messages.append(
            ChatMessage(role="user", content=f"Sources:\n{sources}\n\nQuestion: {question}\n\nAnswer with citations:")
        )
        return messages

    async def _persist_assistant(
        self,
        conversation: Conversation,
        text: str,
        _raw: dict | None,
        citations: list,
        confidence: float,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> Message:
        return await self._messages.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=text,
                model=self._llm.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                confidence=confidence,
                citations=[c.model_dump(mode="json") for c in citations],
            )
        )
