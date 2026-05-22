"""Ingestion job repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.documents.models.ingestion_job import IngestionJob


class IngestionJobRepository(Protocol):
    async def add(self, job: IngestionJob) -> IngestionJob: ...
    async def list_for_document(self, document_id: uuid.UUID) -> Sequence[IngestionJob]: ...


class SqlAlchemyIngestionJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: IngestionJob) -> IngestionJob:
        self._session.add(job)
        await self._session.flush()
        return job

    async def list_for_document(self, document_id: uuid.UUID) -> Sequence[IngestionJob]:
        result = await self._session.execute(
            select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.created_at.asc())
        )
        return result.scalars().all()
