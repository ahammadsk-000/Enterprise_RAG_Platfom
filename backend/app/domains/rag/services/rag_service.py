"""RAG engine: retrieve → compress → generate → cite → score.

Orchestrates a grounded answer for a single query (non-streaming; the streaming
chat variant arrives in Phase 5). Returns the answer with resolved citations, a
confidence score, token usage, and timing.
"""

from __future__ import annotations

import time
import uuid

from app.core.logging import get_logger
from app.domains.rag.citations import build_citations, confidence_score
from app.domains.rag.prompts import build_messages
from app.domains.rag.schemas import RagAnswer, RagQuery
from app.domains.retrieval.compression import compress
from app.domains.retrieval.services.retrieval_service import RetrievalService
from app.integrations.llm.base import LLMProvider

logger = get_logger(__name__)


class RagService:
    def __init__(
        self,
        retrieval: RetrievalService,
        llm: LLMProvider,
        *,
        max_context_tokens: int = 3000,
    ) -> None:
        self._retrieval = retrieval
        self._llm = llm
        self._max_context_tokens = max_context_tokens

    async def answer(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID | None, query: RagQuery
    ) -> RagAnswer:
        start = time.perf_counter()

        retrieved, _ = await self._retrieval.search(
            organization_id=organization_id,
            workspace_id=query.workspace_id,
            query=query.query,
            top_k=query.top_k,
            strategy=query.strategy,
            rerank=query.rerank,
            user_id=user_id,
        )
        context = compress(retrieved, max_tokens=self._max_context_tokens)

        messages = build_messages(query.query, context)
        result = await self._llm.generate(messages, temperature=query.temperature)

        citations = build_citations(result.text, context)
        confidence = confidence_score(result.text, context, citations)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "rag.answer", retrieved=len(retrieved), context=len(context),
            citations=len(citations), confidence=confidence, latency_ms=latency_ms,
        )
        return RagAnswer(
            answer=result.text,
            citations=citations,
            confidence=confidence,
            model=self._llm.model_name,
            strategy=query.strategy,
            retrieved=len(retrieved),
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=latency_ms,
        )
