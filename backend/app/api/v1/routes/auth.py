"""Authentication endpoints: register, login, refresh, me."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep, CurrentPrincipal
from app.domains.identity.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.domains.identity.schemas.user import MeResponse, UserRead

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, service: AuthServiceDep) -> TokenResponse:
    """Create an organization and its owner user, returning auth tokens."""
    result = await service.register(data)
    return result.tokens


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    result = await service.login(data)
    return result.tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    """Rotate the refresh token and issue a fresh access/refresh pair."""
    result = await service.refresh(data.refresh_token)
    return result.tokens


@router.get("/me", response_model=MeResponse)
async def me(principal: CurrentPrincipal, service: AuthServiceDep) -> MeResponse:
    user = await service.get_user(principal.user_id)
    assert user is not None
    return MeResponse(
        user=UserRead.model_validate(user),
        organization_id=principal.organization_id,
        role=principal.role,
        permissions=sorted(principal.permissions),
    )
