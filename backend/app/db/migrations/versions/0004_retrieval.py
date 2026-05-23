"""retrieval_logs + chunks full-text GIN index

Revision ID: 0004_retrieval
Revises: 0003_chunks_embeddings
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_retrieval"
down_revision: str | None = "0003_chunks_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # GIN expression index powering BM25 / full-text search over chunk content.
    op.create_index(
        "ix_chunks_fts",
        "chunks",
        [sa.text("to_tsvector('english', content)")],
        postgresql_using="gin",
    )

    op.create_table(
        "retrieval_logs",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("user_id", _UUID, nullable=True),
        sa.Column("conversation_id", _UUID, nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("strategy", sa.String(20), nullable=False),
        sa.Column("top_k", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("hit_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_ms", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("hits", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_retrieval_logs_organization_id_organizations", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_retrieval_logs_organization_id", "retrieval_logs", ["organization_id"])
    op.create_index("ix_retrieval_logs_created_at", "retrieval_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("retrieval_logs")
    op.drop_index("ix_chunks_fts", table_name="chunks")
