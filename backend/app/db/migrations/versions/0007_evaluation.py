"""eval_datasets, eval_samples, eval_runs, eval_results

Revision ID: 0007_evaluation
Revises: 0006_agents
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_evaluation"
down_revision: str | None = "0006_agents"
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
        "eval_datasets",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(50), server_default="qa", nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_eval_datasets_organization_id_organizations", ondelete="CASCADE"),
    )
    op.create_index("ix_eval_datasets_organization_id", "eval_datasets", ["organization_id"])

    op.create_table(
        "eval_samples",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("dataset_id", _UUID, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("ground_truth", sa.Text(), nullable=True),
        sa.Column("contexts", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["dataset_id"], ["eval_datasets.id"], name="fk_eval_samples_dataset_id_eval_datasets", ondelete="CASCADE"),
    )
    op.create_index("ix_eval_samples_dataset_id", "eval_samples", ["dataset_id"])

    op.create_table(
        "eval_runs",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("dataset_id", _UUID, nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["dataset_id"], ["eval_datasets.id"], name="fk_eval_runs_dataset_id_eval_datasets", ondelete="CASCADE"),
    )
    op.create_index("ix_eval_runs_dataset_id", "eval_runs", ["dataset_id"])

    op.create_table(
        "eval_results",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("eval_run_id", _UUID, nullable=False),
        sa.Column("sample_id", _UUID, nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("scores", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_runs.id"], name="fk_eval_results_eval_run_id_eval_runs", ondelete="CASCADE"),
    )
    op.create_index("ix_eval_results_eval_run_id", "eval_results", ["eval_run_id"])


def downgrade() -> None:
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("eval_samples")
    op.drop_table("eval_datasets")
