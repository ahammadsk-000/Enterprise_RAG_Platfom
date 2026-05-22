"""Permission + Role + role_permissions association.

System roles have `organization_id IS NULL` and `is_system = true` (shared
templates seeded once). Custom org roles set `organization_id`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Table, Column, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Permission(Base, UUIDMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, server_default="org")  # org | workspace
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
