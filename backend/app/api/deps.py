"""Shared FastAPI dependencies: DB session, auth, tenant scoping, RBAC.

Route modules import their dependencies from here so there is a single, stable
surface. Providers (vector/graph/LLM) are added to this module in later phases.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.db.session import get_db
from app.domains.identity.permissions import Permission
from app.domains.identity.repositories.membership_repository import SqlAlchemyMembershipRepository
from app.domains.identity.repositories.oauth_account_repository import SqlAlchemyOAuthAccountRepository
from app.domains.identity.repositories.organization_repository import SqlAlchemyOrganizationRepository
from app.domains.identity.repositories.role_repository import SqlAlchemyRoleRepository
from app.domains.identity.repositories.user_repository import SqlAlchemyUserRepository
from app.domains.identity.schemas.auth import Principal
from app.domains.identity.services.auth_service import AuthService
from app.domains.identity.services.rbac import ensure_permission
from app.domains.documents.repositories.document_repository import SqlAlchemyDocumentRepository
from app.domains.documents.repositories.ingestion_job_repository import SqlAlchemyIngestionJobRepository
from app.domains.documents.services.document_service import DocumentService
from app.domains.ingestion.task_bus import CeleryTaskBus, TaskBus
from app.integrations.storage.factory import get_object_storage

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(
        session=session,
        users=SqlAlchemyUserRepository(session),
        organizations=SqlAlchemyOrganizationRepository(session),
        memberships=SqlAlchemyMembershipRepository(session),
        roles=SqlAlchemyRoleRepository(session),
        oauth_accounts=SqlAlchemyOAuthAccountRepository(session),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_principal(
    service: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise AuthError("Missing bearer token.")
    return await service.principal_from_access_token(credentials.credentials)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def require_permission(
    permission: Permission,
) -> Callable[[Principal], Coroutine[Any, Any, Principal]]:
    """Return a dependency that enforces `permission` on the current principal."""

    async def _dependency(principal: CurrentPrincipal) -> Principal:
        ensure_permission(principal, permission)
        return principal

    return _dependency


# ── Documents / ingestion ────────────────────────────────────────────────────
def get_task_bus() -> TaskBus:
    """Default task bus (Celery). Overridden in tests with a NullTaskBus."""
    return CeleryTaskBus()


TaskBusDep = Annotated[TaskBus, Depends(get_task_bus)]


def get_document_service(session: DbSession, task_bus: TaskBusDep) -> DocumentService:
    return DocumentService(
        session=session,
        documents=SqlAlchemyDocumentRepository(session),
        jobs=SqlAlchemyIngestionJobRepository(session),
        storage=get_object_storage(),
        task_bus=task_bus,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
