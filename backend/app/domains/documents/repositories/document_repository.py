"""Document repository: tenant-scoped persistence + duplicate lookup."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.documents.models.document import Document


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> Document: ...
    async def get(self, document_id: uuid.UUID) -> Document | None: ...
    async def find_duplicate(self, organization_id: uuid.UUID, content_hash: str) -> Document | None: ...
    async def list(
        self, organization_id: uuid.UUID, *, workspace_id: uuid.UUID | None, limit: int, offset: int
    ) -> tuple[Sequence[Document], int]: ...
    async def delete(self, document: Document) -> None: ...


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> Document:
        self._session.add(document)
        await self._session.flush()
        return document

    async def get(self, document_id: uuid.UUID) -> Document | None:
        return await self._session.get(Document, document_id)

    async def find_duplicate(self, organization_id: uuid.UUID, content_hash: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(
                Document.organization_id == organization_id,
                Document.content_hash == content_hash,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def list(
        self, organization_id: uuid.UUID, *, workspace_id: uuid.UUID | None, limit: int, offset: int
    ) -> tuple[Sequence[Document], int]:
        conditions = [Document.organization_id == organization_id]
        if workspace_id is not None:
            conditions.append(Document.workspace_id == workspace_id)

        total = await self._session.scalar(
            select(func.count()).select_from(Document).where(*conditions)
        )
        result = await self._session.execute(
            select(Document).where(*conditions).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        )
        return result.scalars().all(), int(total or 0)

    async def delete(self, document: Document) -> None:
        await self._session.delete(document)
        await self._session.flush()
