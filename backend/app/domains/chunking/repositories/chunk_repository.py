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
