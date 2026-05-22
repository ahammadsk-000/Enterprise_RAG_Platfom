"""User/membership endpoints (tenant-scoped, RBAC-gated)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import AuthServiceDep, CurrentPrincipal, DbSession, require_permission
from app.domains.identity.permissions import Permission
from app.domains.identity.repositories.membership_repository import SqlAlchemyMembershipRepository

router = APIRouter()


class MemberRead(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    status: str


@router.get(
    "/members",
    response_model=list[MemberRead],
    dependencies=[Depends(require_permission(Permission.MEMBERS_READ))],
)
async def list_members(principal: CurrentPrincipal, session: DbSession) -> list[MemberRead]:
    """List members of the caller's active organization."""
    assert principal.organization_id is not None
    repo = SqlAlchemyMembershipRepository(session)
    memberships = await repo.list_for_org(principal.organization_id)
    return [
        MemberRead(user_id=m.user_id, role_id=m.role_id, status=m.status) for m in memberships
    ]
