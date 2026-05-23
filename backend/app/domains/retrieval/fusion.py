"""Reciprocal Rank Fusion (RRF) for combining ranked result lists.

RRF score for a document = Σ 1/(k + rank) across the lists it appears in. It is
robust to score-scale differences between dense and BM25 retrievers, which is why
it is the default fusion for hybrid search.
"""

from __future__ import annotations

from app.domains.retrieval.schemas import RetrievedChunk


def reciprocal_rank_fusion(
    rankings: list[list[RetrievedChunk]], *, k: int = 60
) -> list[RetrievedChunk]:
    scores: dict = {}
    merged: dict = {}
    sources: dict = {}

    for ranking in rankings:
        for rank, chunk in enumerate(ranking):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank + 1)
            merged.setdefault(chunk.chunk_id, chunk)
            sources.setdefault(chunk.chunk_id, set()).add(chunk.source)

    fused: list[RetrievedChunk] = []
    for chunk_id, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
        chunk = merged[chunk_id]
        chunk.score = score
        chunk.source = "hybrid" if len(sources[chunk_id]) > 1 else next(iter(sources[chunk_id]))
        fused.append(chunk)
    return fused
