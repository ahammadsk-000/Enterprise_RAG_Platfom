"""Workspace management endpoints (tenant-scoped, RBAC-gated)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentPrincipal, WorkspaceServiceDep, require_permission
from app.domains.identity.permissions import Permission
from app.domains.workspaces.schemas.workspace import WorkspaceCreate, WorkspaceRead

router = APIRouter()


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def create_workspace(
    data: WorkspaceCreate, principal: CurrentPrincipal, service: WorkspaceServiceDep
) -> WorkspaceRead:
    assert principal.organization_id is not None
    ws = await service.create(organization_id=principal.organization_id, created_by=principal.user_id, data=data)
    return WorkspaceRead.model_validate(ws)


@router.get(
    "",
    response_model=list[WorkspaceRead],
    dependencies=[Depends(require_permission(Permission.WORKSPACE_READ))],
)
async def list_workspaces(principal: CurrentPrincipal, service: WorkspaceServiceDep) -> list[WorkspaceRead]:
    assert principal.organization_id is not None
    return [WorkspaceRead.model_validate(w) for w in await service.list(principal.organization_id)]


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_READ))],
)
async def get_workspace(
    workspace_id: uuid.UUID, principal: CurrentPrincipal, service: WorkspaceServiceDep
) -> WorkspaceRead:
    assert principal.organization_id is not None
    return WorkspaceRead.model_validate(await service.get(workspace_id, principal.organization_id))


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def delete_workspace(
    workspace_id: uuid.UUID, principal: CurrentPrincipal, service: WorkspaceServiceDep
) -> None:
    assert principal.organization_id is not None
    await service.delete(workspace_id, principal.organization_id)
