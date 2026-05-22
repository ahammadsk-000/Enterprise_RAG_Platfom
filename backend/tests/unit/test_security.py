"""Unit tests for password hashing and JWT issuance/verification (no DB)."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import AuthError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip() -> None:
    uid = str(uuid.uuid4())
    org = str(uuid.uuid4())
    token = create_access_token(uid, org)
    payload = decode_token(token, expected_type="access")
    assert payload.sub == uid
    assert payload.org == org
    assert payload.type == "access"
    assert payload.jti


def test_decode_rejects_wrong_token_type() -> None:
    token = create_refresh_token(str(uuid.uuid4()), None)
    with pytest.raises(AuthError):
        decode_token(token, expected_type="access")


def test_decode_rejects_garbage() -> None:
    with pytest.raises(AuthError):
        decode_token("not-a-jwt", expected_type="access")
