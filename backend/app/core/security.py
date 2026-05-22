"""Security primitives: password hashing (argon2) and JWT issuance/verification.

Tokens are signed with HS256 by default (set `AUTH_ALGORITHM=RS256` + key material
in production). Access and refresh tokens carry the subject (user id), the active
organization, a type discriminator, and a unique `jti` enabling future revocation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

TokenType = Literal["access", "refresh"]


class TokenPayload(BaseModel):
    sub: str          # user id
    org: str | None   # active organization id
    type: TokenType
    jti: str
    exp: int
    iat: int


# ── Passwords ────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd_context.verify(password, hashed)


# ── JWT ──────────────────────────────────────────────────────────────────────
def _create_token(
    subject: str,
    organization_id: str | None,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "org": organization_id,
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.auth.secret_key, algorithm=settings.auth.algorithm)


def create_access_token(subject: str, organization_id: str | None) -> str:
    settings = get_settings()
    return _create_token(
        subject, organization_id, "access",
        timedelta(minutes=settings.auth.access_token_ttl_minutes),
    )


def create_refresh_token(subject: str, organization_id: str | None) -> str:
    settings = get_settings()
    return _create_token(
        subject, organization_id, "refresh",
        timedelta(days=settings.auth.refresh_token_ttl_days),
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> TokenPayload:
    """Decode and validate a JWT. Raises `AuthError` on any failure."""
    from app.core.exceptions import AuthError

    settings = get_settings()
    try:
        raw = jwt.decode(token, settings.auth.secret_key, algorithms=[settings.auth.algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid token.") from exc

    payload = TokenPayload(**raw)
    if expected_type is not None and payload.type != expected_type:
        raise AuthError(f"Expected a {expected_type} token.")
    return payload
