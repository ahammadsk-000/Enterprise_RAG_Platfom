"""Embedding provider selection from settings (test env → deterministic fake)."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingProvider


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.llm.embedding_provider
    if settings.environment == "test" or provider == "fake":
        from app.integrations.embeddings.fake import FakeEmbeddingProvider

        return FakeEmbeddingProvider(dim=settings.llm.embedding_dim)

    if provider == "ollama":
        from app.integrations.embeddings.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider(settings.llm)
    if provider == "openai":
        from app.integrations.embeddings.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(settings.llm)

    from app.integrations.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider

    return SentenceTransformersEmbeddingProvider(settings.llm)
