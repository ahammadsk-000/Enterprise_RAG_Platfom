"""Authentication & registration use cases.

`AuthService` orchestrates the identity repositories within the request's unit of
work. It produces an `AuthResult` (issued tokens + a resolved `Principal`) so the
API layer stays thin. Tenant context (role + permissions for the active org) is
resolved from the database on every login/refresh so permission changes propagate.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domains.identity.models.membership import Membership
from app.domains.identity.models.oauth_account import OAuthAccount
from app.domains.identity.models.organization import Organization
from app.domains.identity.models.user import User
from app.domains.identity.permissions import SystemRole
from app.domains.identity.repositories.membership_repository import MembershipRepository
from app.domains.identity.repositories.oauth_account_repository import OAuthAccountRepository
from app.domains.identity.repositories.organization_repository import OrganizationRepository
from app.domains.identity.repositories.role_repository import RoleRepository
from app.domains.identity.repositories.user_repository import UserRepository
from app.domains.identity.schemas.auth import (
    LoginRequest,
    Principal,
    RegisterRequest,
    TokenResponse,
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-")[:255] or "org"


@dataclass(slots=True)
class AuthResult:
    tokens: TokenResponse
    principal: Principal


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        organizations: OrganizationRepository,
        memberships: MembershipRepository,
        roles: RoleRepository,
        oauth_accounts: OAuthAccountRepository,
    ) -> None:
        self._session = session
        self._users = users
        self._orgs = organizations
        self._memberships = memberships
        self._roles = roles
        self._oauth = oauth_accounts

    # ── Use cases ─────────────────────────────────────────────────────────────
    async def register(self, data: RegisterRequest) -> AuthResult:
        email = data.email.lower()
        if await self._users.get_by_email(email):
            raise ConflictError("A user with this email already exists.")

        user = await self._users.add(
            User(email=email, full_name=data.full_name, hashed_password=hash_password(data.password))
        )
        org = await self._provision_owner_org(user, data.organization_name)
        await self._session.commit()

        principal = await self._build_principal(user, org.id)
        return AuthResult(self._issue_tokens(principal), principal)

    async def login(self, data: LoginRequest) -> AuthResult:
        user = await self._users.get_by_email(data.email.lower())
        if user is None or user.hashed_password is None:
            raise AuthError("Invalid email or password.")
        if not verify_password(data.password, user.hashed_password):
            raise AuthError("Invalid email or password.")
        if not user.is_active:
            raise AuthError("Account is disabled.")

        org_id = await self._resolve_login_org(user.id, data.organization_slug)
        await self._users.touch_last_login(user)
        await self._session.commit()

        principal = await self._build_principal(user, org_id)
        return AuthResult(self._issue_tokens(principal), principal)

    async def refresh(self, refresh_token: str) -> AuthResult:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = await self._users.get_by_id(uuid.UUID(payload.sub))
        if user is None or not user.is_active:
            raise AuthError("User no longer exists or is disabled.")
        org_id = uuid.UUID(payload.org) if payload.org else None
        principal = await self._build_principal(user, org_id)
        # Rotation: a fresh access + refresh pair is issued on every refresh.
        return AuthResult(self._issue_tokens(principal), principal)

    async def sso_login(
        self, provider: str, provider_account_id: str, email: str, full_name: str | None
    ) -> AuthResult:
        """Log in (or just-in-time provision) a user from a verified SSO identity."""
        email = email.lower()
        account = await self._oauth.get(provider, provider_account_id)

        if account is not None:
            user = await self._users.get_by_id(account.user_id)
            if user is None:  # pragma: no cover - dangling account
                raise AuthError("Linked account no longer exists.")
        else:
            user = await self._users.get_by_email(email)
            if user is None:
                user = await self._users.add(
                    User(email=email, full_name=full_name, auth_provider=provider, hashed_password=None)
                )
                await self._provision_owner_org(user, f"{full_name or email.split('@')[0]}'s Workspace")
            await self._oauth.add(
                OAuthAccount(
                    user_id=user.id, provider=provider, provider_account_id=provider_account_id, email=email
                )
            )

        if not user.is_active:
            raise AuthError("Account is disabled.")

        memberships = await self._memberships.list_for_user(user.id)
        org_id = memberships[0].organization_id if memberships else None
        await self._users.touch_last_login(user)
        await self._session.commit()

        principal = await self._build_principal(user, org_id)
        return AuthResult(self._issue_tokens(principal), principal)

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self._users.get_by_id(user_id)

    async def principal_from_access_token(self, token: str) -> Principal:
        payload = decode_token(token, expected_type="access")
        user = await self._users.get_by_id(uuid.UUID(payload.sub))
        if user is None or not user.is_active:
            raise AuthError("User no longer exists or is disabled.")
        org_id = uuid.UUID(payload.org) if payload.org else None
        return await self._build_principal(user, org_id)

    # ── Internals ───────────────────────────────────────────────────────────--
    async def _provision_owner_org(self, user: User, org_name: str) -> Organization:
        """Create an organization owned by `user` (shared by register + SSO JIT)."""
        slug = _slugify(org_name)
        if await self._orgs.get_by_slug(slug):
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        org = await self._orgs.add(Organization(name=org_name, slug=slug))
        owner_role = await self._roles.get_system_role(SystemRole.OWNER)
        if owner_role is None:  # pragma: no cover - migration seeds this
            raise NotFoundError("System roles are not seeded; run migrations.")
        await self._memberships.add(
            Membership(organization_id=org.id, user_id=user.id, role_id=owner_role.id)
        )
        return org

    async def _resolve_login_org(self, user_id: uuid.UUID, slug: str | None) -> uuid.UUID:
        if slug:
            org = await self._orgs.get_by_slug(slug)
            if org is None or await self._memberships.get(org.id, user_id) is None:
                raise AuthError("You are not a member of that organization.")
            return org.id
        memberships = await self._memberships.list_for_user(user_id)
        if not memberships:
            raise AuthError("User has no active organization membership.")
        return memberships[0].organization_id

    async def _build_principal(self, user: User, org_id: uuid.UUID | None) -> Principal:
        role_name: str | None = None
        permissions: set[str] = set()
        if org_id is not None:
            membership = await self._memberships.get(org_id, user.id)
            if membership is not None:
                role = await self._roles.get_by_id(membership.role_id)
                role_name = role.name if role else None
                permissions = await self._roles.get_permission_codes(membership.role_id)
        return Principal(
            user_id=user.id,
            email=user.email,
            organization_id=org_id,
            role=role_name,
            permissions=frozenset(permissions),
            is_superuser=user.is_superuser,
        )

    def _issue_tokens(self, principal: Principal) -> TokenResponse:
        settings = get_settings()
        sub = str(principal.user_id)
        org = str(principal.organization_id) if principal.organization_id else None
        return TokenResponse(
            access_token=create_access_token(sub, org),
            refresh_token=create_refresh_token(sub, org),
            expires_in=settings.auth.access_token_ttl_minutes * 60,
        )
