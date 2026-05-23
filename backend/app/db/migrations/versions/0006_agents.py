"""agent_runs + agent_steps

Revision ID: 0006_agents
Revises: 0005_workspaces_chat
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_agents"
down_revision: str | None = "0005_workspaces_chat"
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
        "agent_runs",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("user_id", _UUID, nullable=True),
        sa.Column("graph_name", sa.String(100), server_default="research", nullable=False),
        sa.Column("status", sa.String(20), server_default="running", nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("total_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_agent_runs_organization_id_organizations", ondelete="CASCADE"),
    )
    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"])

    op.create_table(
        "agent_steps",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("agent_run_id", _UUID, nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("node_name", sa.String(50), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("output", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_ms", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], name="fk_agent_steps_agent_run_id_agent_runs", ondelete="CASCADE"),
    )
    op.create_index("ix_agent_steps_agent_run_id", "agent_steps", ["agent_run_id"])


def downgrade() -> None:
    op.drop_table("agent_steps")
    op.drop_table("agent_runs")
