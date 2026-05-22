"""Unit tests for SSO identity extraction and provider gating (no live provider)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.domains.identity.services.oauth_service import extract_identity
from app.main import create_app


def test_extract_identity_google_style() -> None:
    account_id, email, name = extract_identity({"sub": "123", "email": "Owner@Example.com", "name": "Owner"})
    assert account_id == "123"
    assert email == "owner@example.com"  # normalized
    assert name == "Owner"


def test_extract_identity_microsoft_oid_fallback() -> None:
    account_id, email, _ = extract_identity({"oid": "o-9", "email": "m@x.com"})
    assert account_id == "o-9"
    assert email == "m@x.com"


@pytest.mark.asyncio
async def test_unconfigured_provider_returns_404() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/auth/oauth/google/login")
    assert resp.status_code == 404
