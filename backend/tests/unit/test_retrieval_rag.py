"""Unit tests for RetrievalService (fusion+rerank) and RagService end-to-end (fakes)."""

from __future__ import annotations

import uuid

import pytest

from app.domains.rag.schemas import RagQuery
from app.domains.rag.services.rag_service import RagService
from app.domains.retrieval.schemas import RetrievalStrategy, RetrievedChunk
from app.domains.retrieval.services.retrieval_service import RetrievalService
from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.reranker.base import NullReranker


class _FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks

    async def retrieve(self, **_: object) -> list[RetrievedChunk]:
        return list(self._chunks)


def _chunk(content: str, source: str) -> RetrievedChunk:
    return RetrievedChunk(uuid.uuid4(), uuid.uuid4(), content, score=1.0, source=source)


@pytest.mark.asyncio
async def test_hybrid_retrieval_fuses_and_truncates() -> None:
    c1, c2, c3 = _chunk("a", "dense"), _chunk("b", "dense"), _chunk("c", "bm25")
    service = RetrievalService(
        dense=_FakeRetriever([c1, c2]),
        bm25=_FakeRetriever([c2, c3]),  # c2 shared → top after fusion
        reranker=NullReranker(),
    )
    results, latency = await service.search(
        organization_id=uuid.uuid4(),
        workspace_id=None,
        query="q",
        top_k=2,
        strategy=RetrievalStrategy.HYBRID,
        rerank=False,
        persist=False,
    )
    assert len(results) == 2
    assert results[0].chunk_id == c2.chunk_id
    assert latency >= 0


@pytest.mark.asyncio
async def test_rag_service_returns_grounded_answer_with_citations() -> None:
    chunks = [_chunk("The capital is Paris.", "dense"), _chunk("France info.", "bm25")]
    retrieval = RetrievalService(
        dense=_FakeRetriever(chunks), bm25=_FakeRetriever(chunks), reranker=NullReranker()
    )
    rag = RagService(retrieval=retrieval, llm=FakeLLMProvider())

    answer = await rag.answer(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        query=RagQuery(query="What is the capital of France?", top_k=2),
    )
    assert "[1]" in answer.answer
    assert answer.citations and answer.citations[0].marker == 1
    assert answer.model == "fake-llm"
    assert answer.retrieved == 2
    assert 0.0 <= answer.confidence <= 1.0
