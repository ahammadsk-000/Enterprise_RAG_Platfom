"""Agentic retrieval orchestrator.

A typed state machine over specialized roles — planner → retriever → summarizer →
verifier → citation — with a single re-retrieval loop when the answer fails
verification. This is a dependency-free orchestrator with the same shape as a
LangGraph graph; it can be swapped for a LangGraph `StateGraph` without changing the
node logic. Each step is recorded for the agent-activity timeline.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.domains.rag.citations import build_citations, confidence_score
from app.domains.rag.prompts import build_messages
from app.domains.rag.schemas import Citation
from app.domains.retrieval.schemas import RetrievalStrategy, RetrievedChunk
from app.domains.retrieval.services.retrieval_service import RetrievalService
from app.integrations.llm.base import ChatMessage, LLMProvider

logger = get_logger(__name__)

_PLANNER_PROMPT = (
    "Break the user's question into up to 3 focused sub-questions that would help "
    "answer it from a document corpus. Return one sub-question per line.\n\nQuestion: {q}"
)


@dataclass(slots=True)
class AgentStepLog:
    node: str
    role: str
    output: dict
    latency_ms: float


@dataclass(slots=True)
class AgentResult:
    answer: str
    citations: list[Citation]
    confidence: float
    verified: bool
    sub_questions: list[str]
    steps: list[AgentStepLog]
    total_tokens: int


@dataclass(slots=True)
class _State:
    query: str
    sub_questions: list[str] = field(default_factory=list)
    context: list[RetrievedChunk] = field(default_factory=list)
    answer: str = ""
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0
    verified: bool = False
    attempts: int = 0
    total_tokens: int = 0
    steps: list[AgentStepLog] = field(default_factory=list)


class ResearchAgentGraph:
    def __init__(self, retrieval: RetrievalService, llm: LLMProvider) -> None:
        self._retrieval = retrieval
        self._llm = llm

    async def run(
        self,
        *,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        query: str,
        top_k: int = 6,
    ) -> AgentResult:
        state = _State(query=query)
        await self._plan(state)
        await self._retrieve(state, organization_id, workspace_id, user_id, top_k)
        await self._summarize(state)
        await self._verify(state)

        if not state.verified and state.attempts < 1:
            state.attempts += 1
            await self._retrieve(state, organization_id, workspace_id, user_id, top_k * 2)
            await self._summarize(state)
            await self._verify(state)

        return AgentResult(
            answer=state.answer,
            citations=state.citations,
            confidence=state.confidence,
            verified=state.verified,
            sub_questions=state.sub_questions,
            steps=state.steps,
            total_tokens=state.total_tokens,
        )

    # ── nodes ─────────────────────────────────────────────────────────────────
    async def _plan(self, state: _State) -> None:
        start = time.perf_counter()
        result = await self._llm.generate(
            [ChatMessage(role="user", content=_PLANNER_PROMPT.format(q=state.query))], temperature=0.0
        )
        state.total_tokens += result.total_tokens
        questions = [state.query] + [
            ln.strip() for ln in result.text.splitlines() if ln.strip().endswith("?")
        ]
        state.sub_questions = list(dict.fromkeys(questions))[:3]
        self._record(state, "plan", "planner", {"sub_questions": state.sub_questions}, start)

    async def _retrieve(
        self,
        state: _State,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        top_k: int,
    ) -> None:
        start = time.perf_counter()
        merged: dict[uuid.UUID, RetrievedChunk] = {}
        for question in state.sub_questions or [state.query]:
            hits, _ = await self._retrieval.search(
                organization_id=organization_id,
                workspace_id=workspace_id,
                query=question,
                top_k=top_k,
                strategy=RetrievalStrategy.HYBRID,
                rerank=True,
                user_id=user_id,
                persist=False,
            )
            for hit in hits:
                if hit.chunk_id not in merged or hit.score > merged[hit.chunk_id].score:
                    merged[hit.chunk_id] = hit
        state.context = sorted(merged.values(), key=lambda c: c.score, reverse=True)[: top_k + 4]
        self._record(state, "retrieve", "retriever", {"retrieved": len(state.context)}, start)

    async def _summarize(self, state: _State) -> None:
        start = time.perf_counter()
        result = await self._llm.generate(build_messages(state.query, state.context), temperature=0.0)
        state.total_tokens += result.total_tokens
        state.answer = result.text
        self._record(state, "summarize", "summarizer", {"chars": len(result.text)}, start)

    async def _verify(self, state: _State) -> None:
        start = time.perf_counter()
        state.citations = build_citations(state.answer, state.context)
        state.confidence = confidence_score(state.answer, state.context, state.citations)
        state.verified = bool(state.citations) and state.confidence >= 0.3
        self._record(
            state, "verify", "verifier",
            {"verified": state.verified, "confidence": state.confidence, "citations": len(state.citations)},
            start,
        )

    def _record(self, state: _State, node: str, role: str, output: dict, start: float) -> None:
        state.steps.append(
            AgentStepLog(node=node, role=role, output=output, latency_ms=round((time.perf_counter() - start) * 1000, 2))
        )
