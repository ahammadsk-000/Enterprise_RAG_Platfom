"""In-memory vector store (cosine similarity) for tests and local development."""

from __future__ import annotations

import math
import uuid
from typing import Any

from app.integrations.vectorstore.base import SearchHit, VectorPoint


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._collections: dict[str, dict[uuid.UUID, VectorPoint]] = {}

    async def ensure_collection(self, collection: str, dim: int) -> None:
        self._collections.setdefault(collection, {})

    async def upsert(self, collection: str, points: list[VectorPoint]) -> None:
        store = self._collections.setdefault(collection, {})
        for point in points:
            store[point.id] = point

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        store = self._collections.get(collection, {})
        hits = [
            SearchHit(id=p.id, score=_cosine(query_vector, p.vector), payload=p.payload)
            for p in store.values()
            if _matches(p.payload, filters)
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    async def delete_by_document(self, collection: str, document_id: uuid.UUID) -> None:
        store = self._collections.get(collection, {})
        doc = str(document_id)
        for pid in [pid for pid, p in store.items() if str(p.payload.get("document_id")) == doc]:
            del store[pid]


def _matches(payload: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    return all(str(payload.get(k)) == str(v) for k, v in filters.items())
