"""Embedding service — embeds chunks (cached, batched) and indexes vectors.

Resolves/creates the active `EmbeddingVersion`, embeds only chunks flagged for
embedding (children in parent/child strategies), reuses cached vectors by content
hash, upserts into the tenant's vector collection, and records `vector_id` +
`embedding_version_id` back on each chunk.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chunking.models.chunk import Chunk
from app.domains.documents.models.document import Document
from app.domains.embeddings.repositories.embedding_version_repository import EmbeddingVersionRepository
from app.integrations.cache.embedding_cache import EmbeddingCache
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.vectorstore.base import VectorPoint, VectorStore
from app.integrations.vectorstore.factory import collection_name


class EmbeddingService:
    def __init__(
        self,
        session: AsyncSession,
        versions: EmbeddingVersionRepository,
        provider: EmbeddingProvider,
        vector_store: VectorStore,
        cache: EmbeddingCache,
    ) -> None:
        self._session = session
        self._versions = versions
        self._provider = provider
        self._vectors = vector_store
        self._cache = cache

    async def embed_and_index(self, document: Document, chunks: list[Chunk]) -> int:
        version = await self._versions.get_or_create(
            provider=self._provider.provider,
            model_name=self._provider.model_name,
            dim=self._provider.dim,
            normalize=self._provider.normalize,
        )
        targets = [c for c in chunks if c.chunk_metadata.get("embed", True)]
        if not targets:
            return 0

        vectors = await self._resolve_vectors(version.id, targets)

        collection = collection_name(document.organization_id)
        await self._vectors.ensure_collection(collection, version.dim)

        points: list[VectorPoint] = []
        for chunk, vector in zip(targets, vectors, strict=True):
            chunk.vector_id = uuid.uuid4()
            chunk.embedding_version_id = version.id
            points.append(
                VectorPoint(
                    id=chunk.vector_id,
                    vector=vector,
                    payload={
                        "organization_id": str(document.organization_id),
                        "workspace_id": str(document.workspace_id) if document.workspace_id else None,
                        "document_id": str(document.id),
                        "chunk_id": str(chunk.id),
                        "embedding_version_id": str(version.id),
                        "page_from": chunk.page_from,
                        "chunk_type": chunk.chunk_type,
                    },
                )
            )
        await self._vectors.upsert(collection, points)
        await self._session.flush()
        return len(points)

    async def _resolve_vectors(self, version_id: uuid.UUID, chunks: list[Chunk]) -> list[list[float]]:
        vectors: list[list[float] | None] = []
        missing_idx: list[int] = []
        for i, chunk in enumerate(chunks):
            cached = await self._cache.get(f"{version_id}:{chunk.content_hash}")
            vectors.append(cached)
            if cached is None:
                missing_idx.append(i)

        if missing_idx:
            embedded = await self._provider.embed_texts([chunks[i].content for i in missing_idx])
            for slot, vec in zip(missing_idx, embedded, strict=True):
                vectors[slot] = vec
                await self._cache.set(f"{version_id}:{chunks[slot].content_hash}", vec)

        return [v for v in vectors if v is not None]
