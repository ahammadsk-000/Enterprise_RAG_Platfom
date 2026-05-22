"""EmbeddingVersion ORM model.

Captures the (provider, model, dim, normalization, params) tuple used to embed a
set of chunks. Chunks reference their version so re-embedding with a new model is an
incremental, reversible operation rather than a destructive rebuild.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class EmbeddingVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "embedding_versions"
    __table_args__ = (
        UniqueConstraint("provider", "model_name", "dim", name="uq_embedding_version_provider_model_dim"),
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    normalize: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict)
