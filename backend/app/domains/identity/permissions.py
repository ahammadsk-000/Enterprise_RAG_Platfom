"""Canonical permission codes, system roles, and their default permission sets.

This is the single source of truth for RBAC. The initial Alembic migration seeds
`permissions`, system `roles`, and `role_permissions` from these definitions.
"""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    """Fine-grained permission codes (`resource:action`)."""

    ORG_READ = "org:read"
    ORG_ADMIN = "org:admin"
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    WORKSPACE_ADMIN = "workspace:admin"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_WRITE = "documents:write"
    DOCUMENTS_DELETE = "documents:delete"
    CHAT_READ = "chat:read"
    CHAT_WRITE = "chat:write"
    SEARCH_READ = "search:read"
    AGENTS_RUN = "agents:run"
    ANALYTICS_READ = "analytics:read"
    MEMBERS_READ = "members:read"
    MEMBERS_INVITE = "members:invite"
    MEMBERS_MANAGE = "members:manage"
    APIKEYS_MANAGE = "apikeys:manage"
    AUDIT_READ = "audit:read"


class SystemRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ALL_PERMISSIONS: list[Permission] = list(Permission)

_READ_ONLY: set[Permission] = {
    Permission.ORG_READ,
    Permission.WORKSPACE_READ,
    Permission.DOCUMENTS_READ,
    Permission.CHAT_READ,
    Permission.SEARCH_READ,
    Permission.MEMBERS_READ,
}

_MEMBER: set[Permission] = _READ_ONLY | {
    Permission.WORKSPACE_WRITE,
    Permission.DOCUMENTS_WRITE,
    Permission.CHAT_WRITE,
    Permission.AGENTS_RUN,
}

# Admin gets everything except transferring/deleting the org (ORG_ADMIN = owner-only).
_ADMIN: set[Permission] = set(ALL_PERMISSIONS) - {Permission.ORG_ADMIN}

ROLE_PERMISSIONS: dict[SystemRole, set[Permission]] = {
    SystemRole.OWNER: set(ALL_PERMISSIONS),
    SystemRole.ADMIN: _ADMIN,
    SystemRole.MEMBER: _MEMBER,
    SystemRole.VIEWER: _READ_ONLY,
}

PERMISSION_DESCRIPTIONS: dict[Permission, str] = {
    Permission.ORG_READ: "View organization details",
    Permission.ORG_ADMIN: "Administer organization (transfer/delete, billing)",
    Permission.WORKSPACE_READ: "View workspaces",
    Permission.WORKSPACE_WRITE: "Create/update workspace content",
    Permission.WORKSPACE_ADMIN: "Administer workspace settings",
    Permission.DOCUMENTS_READ: "Read documents",
    Permission.DOCUMENTS_WRITE: "Upload/ingest documents",
    Permission.DOCUMENTS_DELETE: "Delete documents",
    Permission.CHAT_READ: "View conversations",
    Permission.CHAT_WRITE: "Send chat messages / run RAG",
    Permission.SEARCH_READ: "Run searches",
    Permission.AGENTS_RUN: "Run agentic workflows",
    Permission.ANALYTICS_READ: "View analytics dashboards",
    Permission.MEMBERS_READ: "View members",
    Permission.MEMBERS_INVITE: "Invite members",
    Permission.MEMBERS_MANAGE: "Manage members and roles",
    Permission.APIKEYS_MANAGE: "Manage API keys",
    Permission.AUDIT_READ: "Read audit logs",
}
