"""Role repository: resolves system roles and their permission sets."""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.models.permission import Permission, Role, role_permissions


class RoleRepository(Protocol):
    async def get_by_id(self, role_id: uuid.UUID) -> Role | None: ...
    async def get_system_role(self, name: str) -> Role | None: ...
    async def get_permission_codes(self, role_id: uuid.UUID) -> set[str]: ...


class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, role_id: uuid.UUID) -> Role | None:
        return await self._session.get(Role, role_id)

    async def get_system_role(self, name: str) -> Role | None:
        result = await self._session.execute(
            select(Role).where(Role.name == name, Role.is_system.is_(True), Role.organization_id.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_permission_codes(self, role_id: uuid.UUID) -> set[str]:
        result = await self._session.execute(
            select(Permission.code)
            .join(role_permissions, role_permissions.c.permission_id == Permission.id)
            .where(role_permissions.c.role_id == role_id)
        )
        return set(result.scalars().all())
