"""Membership repository: links users to organizations with a role."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.models.membership import Membership


class MembershipRepository(Protocol):
    async def get(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> Membership | None: ...
    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Membership]: ...
    async def list_for_org(self, organization_id: uuid.UUID) -> Sequence[Membership]: ...
    async def add(self, membership: Membership) -> Membership: ...


class SqlAlchemyMembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> Membership | None:
        result = await self._session.execute(
            select(Membership).where(
                Membership.organization_id == organization_id,
                Membership.user_id == user_id,
                Membership.workspace_id.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Membership]:
        result = await self._session.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.workspace_id.is_(None),
                Membership.status == "active",
            )
        )
        return result.scalars().all()

    async def list_for_org(self, organization_id: uuid.UUID) -> Sequence[Membership]:
        result = await self._session.execute(
            select(Membership).where(Membership.organization_id == organization_id)
        )
        return result.scalars().all()

    async def add(self, membership: Membership) -> Membership:
        self._session.add(membership)
        await self._session.flush()
        return membership
