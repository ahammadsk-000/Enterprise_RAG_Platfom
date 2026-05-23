"""Unit tests for RRF fusion and context compression."""

from __future__ import annotations

import uuid

from app.domains.retrieval.compression import compress
from app.domains.retrieval.fusion import reciprocal_rank_fusion
from app.domains.retrieval.schemas import RetrievedChunk


def _chunk(content: str = "x", source: str = "dense", score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), content=content, score=score, source=source
    )


def test_rrf_ranks_shared_results_highest() -> None:
    shared_id = uuid.uuid4()
    c1, c3 = _chunk(source="dense"), _chunk(source="bm25")
    # The same chunk surfaces from both retrievers (different source labels).
    c2_dense = RetrievedChunk(shared_id, uuid.uuid4(), "shared", score=1.0, source="dense")
    c2_bm25 = RetrievedChunk(shared_id, uuid.uuid4(), "shared", score=1.0, source="bm25")

    fused = reciprocal_rank_fusion([[c1, c2_dense], [c2_bm25, c3]])
    assert fused[0].chunk_id == shared_id        # appears in both lists → highest
    assert fused[0].source == "hybrid"
    assert {c.chunk_id for c in fused} == {c1.chunk_id, shared_id, c3.chunk_id}


def test_compress_dedupes_and_respects_budget() -> None:
    big = "word " * 200  # ~250 tokens
    chunks = [_chunk(big), _chunk(big), _chunk("unique tail content")]
    kept = compress(chunks, max_tokens=300)
    # duplicate of the first is dropped; budget stops before the dedup'd set blows past
    contents = [c.content for c in kept]
    assert contents.count(big) == 1


def test_compress_keeps_at_least_one() -> None:
    kept = compress([_chunk("a " * 5000)], max_tokens=10)
    assert len(kept) == 1
