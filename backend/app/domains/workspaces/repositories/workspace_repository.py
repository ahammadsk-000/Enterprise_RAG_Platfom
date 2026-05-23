"""Workspace + Memory repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.workspaces.models.workspace import Memory, Workspace


class WorkspaceRepository(Protocol):
    async def add(self, workspace: Workspace) -> Workspace: ...
    async def get(self, workspace_id: uuid.UUID) -> Workspace | None: ...
    async def get_by_slug(self, organization_id: uuid.UUID, slug: str) -> Workspace | None: ...
    async def list_for_org(self, organization_id: uuid.UUID) -> Sequence[Workspace]: ...
    async def delete(self, workspace: Workspace) -> None: ...


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workspace: Workspace) -> Workspace:
        self._session.add(workspace)
        await self._session.flush()
        return workspace

    async def get(self, workspace_id: uuid.UUID) -> Workspace | None:
        return await self._session.get(Workspace, workspace_id)

    async def get_by_slug(self, organization_id: uuid.UUID, slug: str) -> Workspace | None:
        result = await self._session.execute(
            select(Workspace).where(Workspace.organization_id == organization_id, Workspace.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_for_org(self, organization_id: uuid.UUID) -> Sequence[Workspace]:
        result = await self._session.execute(
            select(Workspace).where(Workspace.organization_id == organization_id).order_by(Workspace.created_at.desc())
        )
        return result.scalars().all()

    async def delete(self, workspace: Workspace) -> None:
        await self._session.delete(workspace)
        await self._session.flush()


class MemoryRepository:
    """Long-term memory store (no vector index in this phase; recency + salience ordered)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, memory: Memory) -> Memory:
        self._session.add(memory)
        await self._session.flush()
        return memory

    async def recall(self, organization_id: uuid.UUID, owner_id: uuid.UUID, limit: int = 5) -> Sequence[Memory]:
        result = await self._session.execute(
            select(Memory)
            .where(Memory.organization_id == organization_id, Memory.owner_id == owner_id)
            .order_by(Memory.salience.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
