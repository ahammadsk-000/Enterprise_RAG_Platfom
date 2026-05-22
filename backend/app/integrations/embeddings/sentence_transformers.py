"""Local SentenceTransformers embedding provider (lazy, GPU-capable)."""

from __future__ import annotations

import asyncio

from app.core.config import LLMSettings
from app.core.exceptions import ProviderError


class SentenceTransformersEmbeddingProvider:
    provider = "sentence_transformers"

    def __init__(self, settings: LLMSettings) -> None:
        self.model_name = settings.embedding_model
        self.dim = settings.embedding_dim
        self.normalize = True
        self._model = None

    def _load(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ProviderError("sentence-transformers is not installed.") from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        def _run() -> list[list[float]]:
            model = self._load()
            vectors = model.encode(texts, normalize_embeddings=self.normalize, convert_to_numpy=True)
            return [v.tolist() for v in vectors]

        return await asyncio.to_thread(_run)
