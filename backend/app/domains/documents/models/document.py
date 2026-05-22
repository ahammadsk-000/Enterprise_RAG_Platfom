"""Document ORM model — authoritative metadata for an ingested file.

Raw bytes and the extracted-text artifact live in object storage; this row holds
the metadata and provenance that ties storage, vectors (Phase 3), and the graph
(Phase 6) together. `content_hash` powers duplicate detection within a tenant.
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domains.documents.enums import DocumentStatus


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_org_hash", "organization_id", "content_hash"),
        Index("ix_documents_org_workspace", "organization_id", "workspace_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # FK to workspaces added in Phase 5 (table does not exist yet).
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    text_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=DocumentStatus.UPLOADED.value
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    doc_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict
    )
