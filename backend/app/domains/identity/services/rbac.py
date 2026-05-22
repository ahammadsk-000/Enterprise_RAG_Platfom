"""RBAC policy helpers operating on a `Principal`.

The API layer turns these into FastAPI dependencies (`require_permission`); services
can call `ensure_permission` directly for defense-in-depth.
"""

from __future__ import annotations

from app.core.exceptions import PermissionError as DomainPermissionError
from app.domains.identity.permissions import Permission
from app.domains.identity.schemas.auth import Principal


def ensure_permission(principal: Principal, permission: Permission | str) -> None:
    """Raise `PermissionError` unless the principal holds the permission."""
    if not principal.has_permission(permission):
        raise DomainPermissionError(
            f"Missing required permission: {permission}",
            extra={"required_permission": str(permission)},
        )


def ensure_same_tenant(principal: Principal, organization_id) -> None:  # type: ignore[no-untyped-def]
    """Guard against cross-tenant access even when an id is known/guessed."""
    if principal.is_superuser:
        return
    if principal.organization_id is None or principal.organization_id != organization_id:
        raise DomainPermissionError("Resource belongs to a different organization.")
