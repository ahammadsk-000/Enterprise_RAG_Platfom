"""User DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superuser: bool
    auth_provider: str
    last_login_at: datetime | None
    created_at: datetime


class MeResponse(BaseModel):
    """Current user + active-org context returned to the frontend after login."""

    user: UserRead
    organization_id: uuid.UUID | None
    role: str | None
    permissions: list[str]
