"""Embedding cache — avoids re-embedding identical chunk content.

Keyed by `<embedding_version>:<content_hash>`. `InMemoryEmbeddingCache` is used in
tests/dev; `NullEmbeddingCache` disables caching. A Redis-backed implementation can
be added behind the same Protocol for production.
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingCache(Protocol):
    async def get(self, key: str) -> list[float] | None: ...
    async def set(self, key: str, vector: list[float]) -> None: ...


class NullEmbeddingCache:
    async def get(self, key: str) -> list[float] | None:
        return None

    async def set(self, key: str, vector: list[float]) -> None:
        return None


class InMemoryEmbeddingCache:
    def __init__(self) -> None:
        self._store: dict[str, list[float]] = {}

    async def get(self, key: str) -> list[float] | None:
        return self._store.get(key)

    async def set(self, key: str, vector: list[float]) -> None:
        self._store[key] = vector


def get_embedding_cache() -> EmbeddingCache:
    from app.core.config import get_settings

    if get_settings().environment == "test":
        return InMemoryEmbeddingCache()
    return NullEmbeddingCache()  # Redis-backed cache wired in the observability/perf phase
