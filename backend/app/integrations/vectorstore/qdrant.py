"""Qdrant vector store (lazy client).

Collections use cosine distance. Payloads carry tenant/document fields and are
indexed for filtered search. The qdrant-client is imported lazily so the module
loads without the dependency.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.config import QdrantSettings
from app.core.exceptions import ProviderError
from app.integrations.vectorstore.base import SearchHit, VectorPoint


class QdrantVectorStore:
    def __init__(self, settings: QdrantSettings) -> None:
        self._settings = settings
        self._client = self._build_client(settings)
        self._ensured: set[str] = set()

    @staticmethod
    def _build_client(settings: QdrantSettings):  # type: ignore[no-untyped-def]
        try:
            from qdrant_client import AsyncQdrantClient  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError("qdrant-client is not installed.") from exc
        return AsyncQdrantClient(host=settings.host, port=settings.port, api_key=settings.api_key)

    async def ensure_collection(self, collection: str, dim: int) -> None:
        from qdrant_client import models  # noqa: PLC0415

        if collection in self._ensured:
            return
        if not await self._client.collection_exists(collection):
            await self._client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )
        self._ensured.add(collection)

    async def upsert(self, collection: str, points: list[VectorPoint]) -> None:
        from qdrant_client import models  # noqa: PLC0415

        await self._client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(id=str(p.id), vector=p.vector, payload=p.payload) for p in points
            ],
        )

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        from qdrant_client import models  # noqa: PLC0415

        query_filter = None
        if filters:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(key=k, match=models.MatchValue(value=v))
                    for k, v in filters.items()
                ]
            )
        result = await self._client.query_points(
            collection_name=collection, query=query_vector, limit=limit, query_filter=query_filter
        )
        return [
            SearchHit(id=uuid.UUID(str(p.id)), score=float(p.score), payload=p.payload or {})
            for p in result.points
        ]

    async def delete_by_document(self, collection: str, document_id: uuid.UUID) -> None:
        from qdrant_client import models  # noqa: PLC0415

        await self._client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id", match=models.MatchValue(value=str(document_id))
                        )
                    ]
                )
            ),
        )
