"""Chunk repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chunking.models.chunk import Chunk


class ChunkRepository(Protocol):
    async def add_all(self, chunks: list[Chunk]) -> None: ...
    async def list_for_document(self, document_id: uuid.UUID) -> Sequence[Chunk]: ...
    async def count_for_document(self, document_id: uuid.UUID) -> int: ...
    async def delete_for_document(self, document_id: uuid.UUID) -> None: ...
    async def get_by_ids(self, ids: list[uuid.UUID]) -> Sequence[Chunk]: ...
    async def search_fulltext(
        self, *, organization_id: uuid.UUID, workspace_id: uuid.UUID | None, query: str, limit: int
    ) -> list[tuple[Chunk, float]]: ...


class SqlAlchemyChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_all(self, chunks: list[Chunk]) -> None:
        self._session.add_all(chunks)
        await self._session.flush()

    async def list_for_document(self, document_id: uuid.UUID) -> Sequence[Chunk]:
        result = await self._session.execute(
            select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.ordinal.asc())
        )
        return result.scalars().all()

    async def count_for_document(self, document_id: uuid.UUID) -> int:
        total = await self._session.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
        )
        return int(total or 0)

    async def delete_for_document(self, document_id: uuid.UUID) -> None:
        await self._session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        await self._session.flush()

    async def get_by_ids(self, ids: list[uuid.UUID]) -> Sequence[Chunk]:
        if not ids:
            return []
        result = await self._session.execute(select(Chunk).where(Chunk.id.in_(ids)))
        return result.scalars().all()

    async def search_fulltext(
        self, *, organization_id: uuid.UUID, workspace_id: uuid.UUID | None, query: str, limit: int
    ) -> list[tuple[Chunk, float]]:
        tsvector = func.to_tsvector("english", Chunk.content)
        tsquery = func.plainto_tsquery("english", query)
        rank = func.ts_rank(tsvector, tsquery)

        conditions = [Chunk.organization_id == organization_id, tsvector.op("@@")(tsquery)]
        if workspace_id is not None:
            conditions.append(Chunk.workspace_id == workspace_id)

        result = await self._session.execute(
            select(Chunk, rank.label("rank")).where(*conditions).order_by(rank.desc()).limit(limit)
        )
        return [(row[0], float(row[1])) for row in result.all()]
