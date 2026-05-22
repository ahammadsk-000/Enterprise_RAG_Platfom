"""initial identity schema (orgs, users, roles, permissions, memberships, api keys, oauth)

Revision ID: 0001_initial_identity
Revises:
Create Date: 2026-05-23
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.domains.identity.permissions import (
    PERMISSION_DESCRIPTIONS,
    ROLE_PERMISSIONS,
    SystemRole,
)

revision: str = "0001_initial_identity"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(50), server_default="free", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("auth_provider", sa.String(50), server_default="local", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "permissions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"])

    op.create_table(
        "roles",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scope", sa.String(20), server_default="org", nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_roles_organization_id_organizations", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_roles_organization_id", "roles", ["organization_id"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", _UUID, nullable=False),
        sa.Column("permission_id", _UUID, nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name="fk_role_permissions_role_id_roles", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"], name="fk_role_permissions_permission_id_permissions", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
    )

    op.create_table(
        "memberships",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("role_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_memberships_organization_id_organizations", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_memberships_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name="fk_memberships_role_id_roles", ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "user_id", "workspace_id", name="uq_membership_org_user_ws"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_workspace_id", "memberships", ["workspace_id"])

    op.create_table(
        "api_keys",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("hashed_secret", sa.String(255), nullable=False),
        sa.Column("scopes", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_api_keys_organization_id_organizations", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_api_keys_user_id_users", ondelete="CASCADE"),
        sa.UniqueConstraint("prefix", name="uq_api_keys_prefix"),
    )
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"])
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])

    op.create_table(
        "oauth_accounts",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_account_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_oauth_accounts_user_id_users", ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "provider_account_id", name="uq_oauth_provider_account"),
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])

    _seed_rbac()


def _seed_rbac() -> None:
    """Seed permissions, system roles, and their permission assignments."""
    bind = op.get_bind()

    perm_ids: dict[str, uuid.UUID] = {}
    perm_rows = []
    for code, description in PERMISSION_DESCRIPTIONS.items():
        pid = uuid.uuid4()
        perm_ids[str(code)] = pid
        perm_rows.append({"id": pid, "code": str(code), "description": description})

    permissions_t = sa.table(
        "permissions",
        sa.column("id", _UUID),
        sa.column("code", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(permissions_t, perm_rows)

    roles_t = sa.table(
        "roles",
        sa.column("id", _UUID),
        sa.column("organization_id", _UUID),
        sa.column("name", sa.String),
        sa.column("scope", sa.String),
        sa.column("is_system", sa.Boolean),
    )
    rp_t = sa.table(
        "role_permissions",
        sa.column("role_id", _UUID),
        sa.column("permission_id", _UUID),
    )

    role_rows = []
    rp_rows = []
    for role in SystemRole:
        rid = uuid.uuid4()
        role_rows.append(
            {"id": rid, "organization_id": None, "name": str(role), "scope": "org", "is_system": True}
        )
        for perm in ROLE_PERMISSIONS[role]:
            rp_rows.append({"role_id": rid, "permission_id": perm_ids[str(perm)]})

    op.bulk_insert(roles_t, role_rows)
    op.bulk_insert(rp_t, rp_rows)
    bind  # noqa: B018 - keep bind reference for clarity / future use


def downgrade() -> None:
    for table in (
        "oauth_accounts",
        "api_keys",
        "memberships",
        "role_permissions",
        "roles",
        "permissions",
        "users",
        "organizations",
    ):
        op.drop_table(table)
