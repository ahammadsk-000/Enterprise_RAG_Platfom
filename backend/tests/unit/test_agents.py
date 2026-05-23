"""Unit test for the research agent orchestrator (fakes, no DB)."""

from __future__ import annotations

import uuid

import pytest

from app.domains.agents.graph.orchestrator import ResearchAgentGraph
from app.domains.retrieval.schemas import RetrievedChunk
from app.domains.retrieval.services.retrieval_service import RetrievalService
from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.reranker.base import NullReranker


class _FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks

    async def retrieve(self, **_: object) -> list[RetrievedChunk]:
        return list(self._chunks)


@pytest.mark.asyncio
async def test_research_graph_runs_all_nodes_and_grounds() -> None:
    chunks = [RetrievedChunk(uuid.uuid4(), uuid.uuid4(), "Paris is the capital of France.", 3.0, "dense")]
    retrieval = RetrievalService(_FakeRetriever(chunks), _FakeRetriever(chunks), NullReranker())
    graph = ResearchAgentGraph(retrieval, FakeLLMProvider())

    result = await graph.run(
        organization_id=uuid.uuid4(), workspace_id=None, user_id=uuid.uuid4(),
        query="What is the capital of France?",
    )

    roles = [s.role for s in result.steps]
    assert roles[:4] == ["planner", "retriever", "summarizer", "verifier"]
    assert "[1]" in result.answer
    assert result.citations and result.verified
    # planner always includes the original query among the sub-questions
    assert "What is the capital of France?" in result.sub_questions
