"""Unit tests for citation extraction + confidence scoring."""

from __future__ import annotations

import uuid

from app.domains.rag.citations import build_citations, confidence_score, extract_markers
from app.domains.retrieval.schemas import RetrievedChunk


def _chunk(content: str, score: float = 2.0) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), content=content, score=score, page_from=3
    )


def test_extract_markers_handles_formats() -> None:
    assert extract_markers("foo [1] bar [2][3] baz [1, 4]") == [1, 2, 3, 4]
    assert extract_markers("no citations here") == []


def test_build_citations_resolves_in_range_only() -> None:
    chunks = [_chunk("first source"), _chunk("second source")]
    citations = build_citations("Answer grounded in [1] and [2] but not [5].", chunks)
    assert [c.marker for c in citations] == [1, 2]
    assert citations[0].chunk_id == chunks[0].chunk_id
    assert citations[0].page_from == 3


def test_confidence_low_on_refusal_and_no_context() -> None:
    chunks = [_chunk("ctx")]
    assert confidence_score("I don't have enough information.", chunks, []) == 0.1
    assert confidence_score("anything", [], []) == 0.0


def test_confidence_higher_when_grounded() -> None:
    chunks = [_chunk("a", score=5.0), _chunk("b", score=4.0)]
    cites = build_citations("Grounded [1][2].", chunks)
    score = confidence_score("Grounded [1][2].", chunks, cites)
    assert score > 0.5
