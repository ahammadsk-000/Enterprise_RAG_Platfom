"""Context compression for the RAG prompt.

Deduplicates near-identical chunks (by content hash of normalized text) and packs
the highest-ranked chunks up to a token budget so the prompt stays within the
model's context window while maximizing useful evidence.
"""

from __future__ import annotations

import hashlib

from app.domains.chunking.tokenizer import estimate_tokens
from app.domains.retrieval.schemas import RetrievedChunk


def _norm_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).lower().encode()).hexdigest()


def compress(chunks: list[RetrievedChunk], *, max_tokens: int = 3000) -> list[RetrievedChunk]:
    seen: set[str] = set()
    kept: list[RetrievedChunk] = []
    budget = 0
    for chunk in chunks:
        digest = _norm_hash(chunk.content)
        if digest in seen:
            continue
        tokens = estimate_tokens(chunk.content)
        if budget + tokens > max_tokens and kept:
            break
        seen.add(digest)
        kept.append(chunk)
        budget += tokens
    return kept
