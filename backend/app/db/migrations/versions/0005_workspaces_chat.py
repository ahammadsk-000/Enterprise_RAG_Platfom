"""workspaces, conversations, messages, memories + workspace_id FKs

Revision ID: 0005_workspaces_chat
Revises: 0004_retrieval
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_workspaces_chat"
down_revision: str | None = "0004_retrieval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("chunking_strategy", sa.String(50), server_default="recursive", nullable=False),
        sa.Column("created_by", _UUID, nullable=True),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_workspaces_organization_id_organizations", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_workspaces_created_by_users", ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_workspaces_org_slug"),
    )
    op.create_index("ix_workspaces_organization_id", "workspaces", ["organization_id"])

    op.create_table(
        "memories",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("owner_id", _UUID, nullable=False),
        sa.Column("kind", sa.String(20), server_default="fact", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("salience", sa.Integer(), server_default=sa.text("1"), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_memories_organization_id_organizations", ondelete="CASCADE"),
    )
    op.create_index("ix_memories_organization_id", "memories", ["organization_id"])
    op.create_index("ix_memories_owner_id", "memories", ["owner_id"])

    op.create_table(
        "conversations",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("title", sa.String(512), server_default="New conversation", nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_conversations_organization_id_organizations", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name="fk_conversations_workspace_id_workspaces", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_conversations_user_id_users", ondelete="CASCADE"),
    )
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("conversation_id", _UUID, nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("finish_reason", sa.String(50), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_ms", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("citations", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_messages_conversation_id_conversations", ondelete="CASCADE"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # Backfill FK constraints on the workspace_id placeholders added in earlier phases.
    for table in ("documents", "chunks", "memberships"):
        op.create_foreign_key(
            f"fk_{table}_workspace_id_workspaces", table, "workspaces", ["workspace_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    for table in ("documents", "chunks", "memberships"):
        op.drop_constraint(f"fk_{table}_workspace_id_workspaces", table, type_="foreignkey")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("memories")
    op.drop_table("workspaces")
