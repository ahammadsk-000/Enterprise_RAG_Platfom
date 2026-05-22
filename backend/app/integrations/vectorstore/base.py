"""Vector store interface + value objects.

A collection holds points of a single embedding dimension. Payloads mirror the
tenant/document fields so retrieval can filter without touching Postgres. Search is
defined here but exercised in Phase 4 (hybrid retrieval).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class VectorPoint:
    id: uuid.UUID
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchHit:
    id: uuid.UUID
    score: float
    payload: dict[str, Any]


class VectorStore(Protocol):
    async def ensure_collection(self, collection: str, dim: int) -> None: ...
    async def upsert(self, collection: str, points: list[VectorPoint]) -> None: ...
    async def search(
        self,
        collection: str,
        query_vector: list[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]: ...
    async def delete_by_document(self, collection: str, document_id: uuid.UUID) -> None: ...
