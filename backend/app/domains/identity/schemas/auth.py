"""Auth DTOs and the request `Principal` (authenticated identity + permissions)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domains.identity.permissions import Permission


class RegisterRequest(BaseModel):
    """Self-service signup: creates an organization and its owner user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    organization_name: str = Field(min_length=2, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    # Optional: disambiguate when the user belongs to multiple organizations.
    organization_slug: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access-token TTL in seconds


class Principal(BaseModel):
    """The authenticated caller for the current request."""

    model_config = ConfigDict(frozen=True)

    user_id: uuid.UUID
    email: str
    organization_id: uuid.UUID | None
    role: str | None
    permissions: frozenset[str]
    is_superuser: bool = False

    def has_permission(self, permission: Permission | str) -> bool:
        return self.is_superuser or str(permission) in self.permissions
