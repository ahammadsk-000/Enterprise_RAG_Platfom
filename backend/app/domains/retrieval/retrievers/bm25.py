"""BM25 / keyword retriever backed by PostgreSQL full-text search.

Uses `to_tsvector('english', content) @@ plainto_tsquery(...)` ranked by `ts_rank`,
accelerated by the GIN expression index created in migration 0004. Tenant- and
workspace-scoped at the query level.
"""

from __future__ import annotations

import uuid

from app.domains.chunking.repositories.chunk_repository import ChunkRepository
from app.domains.retrieval.schemas import RetrievedChunk


class BM25Retriever:
    def __init__(self, chunks: ChunkRepository) -> None:
        self._chunks = chunks

    async def retrieve(
        self, *, organization_id: uuid.UUID, workspace_id: uuid.UUID | None, query: str, limit: int
    ) -> list[RetrievedChunk]:
        rows = await self._chunks.search_fulltext(
            organization_id=organization_id, workspace_id=workspace_id, query=query, limit=limit
        )
        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                score=float(rank),
                source="bm25",
                page_from=chunk.page_from,
                page_to=chunk.page_to,
                chunk_type=chunk.chunk_type,
            )
            for chunk, rank in rows
        ]
