"""Unit tests for the RBAC policy helpers (no DB)."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import PermissionError as DomainPermissionError
from app.domains.identity.permissions import Permission, ROLE_PERMISSIONS, SystemRole
from app.domains.identity.schemas.auth import Principal
from app.domains.identity.services.rbac import ensure_permission, ensure_same_tenant


def _principal(permissions: set[str], *, superuser: bool = False, org=None) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        email="a@b.com",
        organization_id=org or uuid.uuid4(),
        role="member",
        permissions=frozenset(permissions),
        is_superuser=superuser,
    )


def test_ensure_permission_allows_when_present() -> None:
    p = _principal({str(Permission.DOCUMENTS_WRITE)})
    ensure_permission(p, Permission.DOCUMENTS_WRITE)  # no raise


def test_ensure_permission_denies_when_missing() -> None:
    p = _principal({str(Permission.DOCUMENTS_READ)})
    with pytest.raises(DomainPermissionError):
        ensure_permission(p, Permission.DOCUMENTS_WRITE)


def test_superuser_bypasses_permission_checks() -> None:
    p = _principal(set(), superuser=True)
    ensure_permission(p, Permission.ORG_ADMIN)  # no raise


def test_viewer_role_is_read_only() -> None:
    viewer = {str(x) for x in ROLE_PERMISSIONS[SystemRole.VIEWER]}
    assert str(Permission.DOCUMENTS_WRITE) not in viewer
    assert str(Permission.DOCUMENTS_READ) in viewer


def test_owner_has_org_admin_but_member_does_not() -> None:
    assert Permission.ORG_ADMIN in ROLE_PERMISSIONS[SystemRole.OWNER]
    assert Permission.ORG_ADMIN not in ROLE_PERMISSIONS[SystemRole.MEMBER]


def test_ensure_same_tenant_blocks_cross_tenant() -> None:
    org_a = uuid.uuid4()
    p = _principal({str(Permission.DOCUMENTS_READ)}, org=org_a)
    ensure_same_tenant(p, org_a)  # no raise
    with pytest.raises(DomainPermissionError):
        ensure_same_tenant(p, uuid.uuid4())
