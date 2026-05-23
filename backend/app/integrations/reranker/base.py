"""Re-ranker interface + implementations.

A re-ranker re-scores (query, passage) pairs with a cross-encoder for higher
precision than the first-stage retrievers. `NullReranker` preserves input order
(used in tests / when reranking is disabled).
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from app.core.exceptions import ProviderError


class Reranker(Protocol):
    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        """Return a relevance score per passage (higher = more relevant)."""
        ...


class NullReranker:
    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        # Descending scores preserve the incoming order after a stable sort.
        return [float(len(passages) - i) for i in range(len(passages))]


class CrossEncoderReranker:
    """sentence-transformers CrossEncoder (lazy; GPU-capable)."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder  # noqa: PLC0415
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ProviderError("sentence-transformers not installed; reranker unavailable.") from exc
            self._model = CrossEncoder(self.model_name)
        return self._model

    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []

        def _run() -> list[float]:
            model = self._load()
            scores = model.predict([(query, p) for p in passages])
            return [float(s) for s in scores]

        return await asyncio.to_thread(_run)
