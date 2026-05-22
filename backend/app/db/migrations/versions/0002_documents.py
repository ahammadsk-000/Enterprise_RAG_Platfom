"""documents + ingestion_jobs

Revision ID: 0002_documents
Revises: 0001_initial_identity
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_documents"
down_revision: str | None = "0001_initial_identity"
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
        "documents",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("created_by", _UUID, nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("source_uri", sa.String(2048), nullable=True),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("text_storage_key", sa.String(1024), nullable=True),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default="uploaded", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_documents_organization_id_organizations", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_documents_created_by_users", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])
    op.create_index("ix_documents_org_hash", "documents", ["organization_id", "content_hash"])
    op.create_index("ix_documents_org_workspace", "documents", ["organization_id", "workspace_id"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("document_id", _UUID, nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name="fk_ingestion_jobs_document_id_documents", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"])


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_table("documents")
