"""Citation extraction + confidence scoring.

Parses bracketed markers (``[1]``, ``[2][3]``, ``[1, 2]``) from the generated answer
and resolves them to the numbered context chunks. Confidence blends retrieval
strength with grounding signals (whether the answer cited sources and how much of
the answer is backed by retrieved evidence).
"""

from __future__ import annotations

import re

from app.domains.rag.schemas import Citation
from app.domains.retrieval.schemas import RetrievedChunk

_MARKER_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_SNIPPET_LEN = 240
_REFUSAL_HINTS = ("don't have enough", "do not have enough", "cannot find", "no information")


def extract_markers(answer: str) -> list[int]:
    """Return the ordered, de-duplicated source numbers referenced in the answer."""
    seen: list[int] = []
    for group in _MARKER_RE.findall(answer):
        for token in group.split(","):
            n = int(token.strip())
            if n not in seen:
                seen.append(n)
    return seen


def build_citations(answer: str, chunks: list[RetrievedChunk]) -> list[Citation]:
    citations: list[Citation] = []
    for marker in extract_markers(answer):
        if 1 <= marker <= len(chunks):
            chunk = chunks[marker - 1]
            citations.append(
                Citation(
                    marker=marker,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    page_from=chunk.page_from,
                    snippet=chunk.content[:_SNIPPET_LEN],
                    score=chunk.score,
                )
            )
    return citations


def confidence_score(answer: str, chunks: list[RetrievedChunk], citations: list[Citation]) -> float:
    """Heuristic confidence in [0, 1]."""
    if not chunks:
        return 0.0
    if any(hint in answer.lower() for hint in _REFUSAL_HINTS):
        return 0.1

    # Normalize the top retrieval score into [0, 1] (scores may be cosine or rerank logits).
    top = max((c.score for c in chunks), default=0.0)
    retrieval_signal = 1.0 / (1.0 + pow(2.718281828, -top)) if top else 0.0  # sigmoid
    grounding_signal = min(1.0, len(citations) / 2.0)  # cited ≥2 sources → full grounding
    return round(0.5 * retrieval_signal + 0.5 * grounding_signal, 3)
