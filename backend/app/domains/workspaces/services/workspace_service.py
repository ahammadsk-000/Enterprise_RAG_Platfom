"""Workspace use cases (tenant-scoped)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.workspaces.models.workspace import Workspace
from app.domains.workspaces.repositories.workspace_repository import WorkspaceRepository
from app.domains.workspaces.schemas.workspace import WorkspaceCreate

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-")[:255] or "workspace"


class WorkspaceService:
    def __init__(self, session: AsyncSession, workspaces: WorkspaceRepository) -> None:
        self._session = session
        self._repo = workspaces

    async def create(
        self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, data: WorkspaceCreate
    ) -> Workspace:
        slug = _slugify(data.name)
        if await self._repo.get_by_slug(organization_id, slug):
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        workspace = await self._repo.add(
            Workspace(
                organization_id=organization_id,
                name=data.name,
                slug=slug,
                description=data.description,
                chunking_strategy=data.chunking_strategy,
                created_by=created_by,
            )
        )
        await self._session.commit()
        return workspace

    async def list(self, organization_id: uuid.UUID) -> Sequence[Workspace]:
        return await self._repo.list_for_org(organization_id)

    async def get(self, workspace_id: uuid.UUID, organization_id: uuid.UUID) -> Workspace:
        workspace = await self._repo.get(workspace_id)
        if workspace is None or workspace.organization_id != organization_id:
            raise NotFoundError("Workspace not found.")
        return workspace

    async def delete(self, workspace_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        workspace = await self.get(workspace_id, organization_id)
        await self._repo.delete(workspace)
        await self._session.commit()

    async def resolve_chunking_strategy(self, workspace_id: uuid.UUID | None) -> str | None:
        if workspace_id is None:
            raise ConflictError("workspace_id required")  # pragma: no cover - guarded by callers
        workspace = await self._repo.get(workspace_id)
        return workspace.chunking_strategy if workspace else None
