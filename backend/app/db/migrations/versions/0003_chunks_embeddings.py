"""embedding_versions + chunks

Revision ID: 0003_chunks_embeddings
Revises: 0002_documents
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_chunks_embeddings"
down_revision: str | None = "0002_documents"
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
        "embedding_versions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("normalize", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("params", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("provider", "model_name", "dim", name="uq_embedding_version_provider_model_dim"),
    )

    op.create_table(
        "chunks",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("organization_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("document_id", _UUID, nullable=False),
        sa.Column("parent_chunk_id", _UUID, nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("chunk_type", sa.String(20), server_default="text", nullable=False),
        sa.Column("token_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("embedding_version_id", _UUID, nullable=True),
        sa.Column("vector_id", _UUID, nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_chunks_organization_id_organizations", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name="fk_chunks_document_id_documents", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parent_chunk_id"], ["chunks.id"], name="fk_chunks_parent_chunk_id_chunks", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["embedding_version_id"], ["embedding_versions.id"], name="fk_chunks_embedding_version_id_embedding_versions", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_chunks_organization_id", "chunks", ["organization_id"])
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_content_hash", "chunks", ["content_hash"])
    op.create_index("ix_chunks_document_ordinal", "chunks", ["document_id", "ordinal"])
    op.create_index("ix_chunks_org_workspace", "chunks", ["organization_id", "workspace_id"])


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("embedding_versions")
