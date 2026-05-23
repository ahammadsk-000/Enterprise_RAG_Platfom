"""Dense (vector ANN) retriever.

Embeds the query, searches the tenant's vector collection with metadata filters,
then hydrates chunk content/provenance from Postgres (vectors stay lean in Qdrant).
"""

from __future__ import annotations

import uuid

from app.domains.chunking.repositories.chunk_repository import ChunkRepository
from app.domains.retrieval.schemas import RetrievedChunk
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.vectorstore.base import VectorStore
from app.integrations.vectorstore.factory import collection_name


class DenseRetriever:
    def __init__(
        self, embedder: EmbeddingProvider, vector_store: VectorStore, chunks: ChunkRepository
    ) -> None:
        self._embedder = embedder
        self._vectors = vector_store
        self._chunks = chunks

    async def retrieve(
        self, *, organization_id: uuid.UUID, workspace_id: uuid.UUID | None, query: str, limit: int
    ) -> list[RetrievedChunk]:
        (query_vector,) = await self._embedder.embed_texts([query])
        filters: dict = {"organization_id": str(organization_id)}
        if workspace_id is not None:
            filters["workspace_id"] = str(workspace_id)

        hits = await self._vectors.search(
            collection_name(organization_id), query_vector, limit=limit, filters=filters
        )
        if not hits:
            return []

        score_by_chunk = {uuid.UUID(h.payload["chunk_id"]): h.score for h in hits if h.payload.get("chunk_id")}
        chunks = await self._chunks.get_by_ids(list(score_by_chunk))
        by_id = {c.id: c for c in chunks}

        results: list[RetrievedChunk] = []
        for chunk_id, score in score_by_chunk.items():
            chunk = by_id.get(chunk_id)
            if chunk is None:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=float(score),
                    source="dense",
                    page_from=chunk.page_from,
                    page_to=chunk.page_to,
                    chunk_type=chunk.chunk_type,
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results
