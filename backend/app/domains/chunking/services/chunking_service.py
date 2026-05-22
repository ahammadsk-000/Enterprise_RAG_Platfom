"""Chunking service — turns a parsed document into persisted `Chunk` rows.

Idempotent: existing chunks for the document are removed first (supports reindexing).
Parent/child links are resolved after flush using the ordinal→id map.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chunking.chunkers.registry import get_chunker
from app.domains.chunking.models.chunk import Chunk
from app.domains.chunking.repositories.chunk_repository import ChunkRepository
from app.domains.documents.models.document import Document
from app.domains.ingestion.parsers.base import ParsedDocument
from app.domains.ingestion.services.metadata import content_hash


class ChunkingService:
    def __init__(self, session: AsyncSession, chunks: ChunkRepository) -> None:
        self._session = session
        self._chunks = chunks

    async def chunk_document(
        self, document: Document, parsed: ParsedDocument, *, strategy: str | None = None
    ) -> list[Chunk]:
        text_chunks = get_chunker(strategy).chunk(parsed)
        await self._chunks.delete_for_document(document.id)

        by_ordinal: dict[int, tuple[Chunk, int | None]] = {}
        orm_chunks: list[Chunk] = []
        for tc in text_chunks:
            chunk = Chunk(
                organization_id=document.organization_id,
                workspace_id=document.workspace_id,
                document_id=document.id,
                ordinal=tc.ordinal,
                content=tc.content,
                content_hash=content_hash(tc.content.encode("utf-8")),
                chunk_type=tc.chunk_type.value,
                token_count=tc.token_count,
                page_from=tc.page_from,
                page_to=tc.page_to,
                chunk_metadata={**tc.metadata, "embed": tc.embed},
            )
            orm_chunks.append(chunk)
            by_ordinal[tc.ordinal] = (chunk, tc.parent_ordinal)

        await self._chunks.add_all(orm_chunks)  # flush assigns ids

        linked = False
        for chunk, parent_ordinal in by_ordinal.values():
            if parent_ordinal is not None and parent_ordinal in by_ordinal:
                chunk.parent_chunk_id = by_ordinal[parent_ordinal][0].id
                linked = True
        if linked:
            await self._session.flush()
        return orm_chunks
