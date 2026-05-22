"""Organization repository: interface + SQLAlchemy implementation."""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.models.organization import Organization


class OrganizationRepository(Protocol):
    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None: ...
    async def get_by_slug(self, slug: str) -> Organization | None: ...
    async def add(self, org: Organization) -> Organization: ...


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        return await self._session.get(Organization, org_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self._session.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def add(self, org: Organization) -> Organization:
        self._session.add(org)
        await self._session.flush()
        return org
