"""Retrieval orchestration: dense + BM25 → RRF fusion → cross-encoder re-rank.

Strategy is selectable per request (dense / bm25 / hybrid). For hybrid, both
first-stage retrievers pull an enlarged candidate pool which is fused with RRF and
optionally re-ranked, then truncated to `top_k`. Each query is logged for analytics.
"""

from __future__ import annotations

import time
import uuid

from app.core.logging import get_logger
from app.domains.retrieval.fusion import reciprocal_rank_fusion
from app.domains.retrieval.models.retrieval_log import RetrievalLog
from app.domains.retrieval.repositories.retrieval_log_repository import RetrievalLogRepository
from app.domains.retrieval.retrievers.base import Retriever
from app.domains.retrieval.schemas import RetrievalStrategy, RetrievedChunk
from app.integrations.reranker.base import Reranker

logger = get_logger(__name__)

_CANDIDATE_MULTIPLIER = 4


class RetrievalService:
    def __init__(
        self,
        dense: Retriever,
        bm25: Retriever,
        reranker: Reranker,
        logs: RetrievalLogRepository | None = None,
    ) -> None:
        self._dense = dense
        self._bm25 = bm25
        self._reranker = reranker
        self._logs = logs

    async def search(
        self,
        *,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        query: str,
        top_k: int = 10,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        rerank: bool = True,
        user_id: uuid.UUID | None = None,
        persist: bool = True,
    ) -> tuple[list[RetrievedChunk], float]:
        start = time.perf_counter()
        candidates = await self._first_stage(organization_id, workspace_id, query, top_k, strategy)
        ranked = await self._maybe_rerank(query, candidates, rerank)
        results = ranked[:top_k]
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if persist and self._logs is not None:
            await self._log(organization_id, workspace_id, user_id, query, strategy, top_k, results, latency_ms)
        return results, latency_ms

    async def _first_stage(
        self,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        query: str,
        top_k: int,
        strategy: RetrievalStrategy,
    ) -> list[RetrievedChunk]:
        pool = top_k * _CANDIDATE_MULTIPLIER
        kwargs = {"organization_id": organization_id, "workspace_id": workspace_id, "query": query, "limit": pool}

        if strategy is RetrievalStrategy.DENSE:
            return await self._dense.retrieve(**kwargs)
        if strategy is RetrievalStrategy.BM25:
            return await self._bm25.retrieve(**kwargs)

        dense_hits = await self._dense.retrieve(**kwargs)
        bm25_hits = await self._bm25.retrieve(**kwargs)
        return reciprocal_rank_fusion([dense_hits, bm25_hits])

    async def _maybe_rerank(
        self, query: str, candidates: list[RetrievedChunk], rerank: bool
    ) -> list[RetrievedChunk]:
        if not rerank or not candidates:
            return candidates
        scores = await self._reranker.rerank(query, [c.content for c in candidates])
        for chunk, score in zip(candidates, scores, strict=True):
            chunk.score = float(score)
        return sorted(candidates, key=lambda c: c.score, reverse=True)

    async def _log(
        self,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        query: str,
        strategy: RetrievalStrategy,
        top_k: int,
        results: list[RetrievedChunk],
        latency_ms: float,
    ) -> None:
        assert self._logs is not None
        await self._logs.add(
            RetrievalLog(
                organization_id=organization_id,
                workspace_id=workspace_id,
                user_id=user_id,
                query=query,
                strategy=strategy.value,
                top_k=top_k,
                hit_count=len(results),
                latency_ms=latency_ms,
                hits=[
                    {"chunk_id": str(r.chunk_id), "document_id": str(r.document_id), "score": r.score, "source": r.source}
                    for r in results
                ],
            )
        )
