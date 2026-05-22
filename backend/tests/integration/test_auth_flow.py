"""End-to-end auth flow against a real Postgres (run with `pytest -m integration`).

Requires a running database with migrations applied (`alembic upgrade head`),
e.g. via `docker compose up -d postgres` + the seeded system roles.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_register_login_me_refresh() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # register → tokens
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "supersecret123",
                "full_name": "Org Owner",
                "organization_name": "Acme Corp",
            },
        )
        assert reg.status_code == 201, reg.text
        tokens = reg.json()
        assert tokens["access_token"] and tokens["refresh_token"]

        # /me with the access token → owner role + permissions
        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert me.status_code == 200, me.text
        body = me.json()
        assert body["user"]["email"] == email
        assert body["role"] == "owner"
        assert "org:admin" in body["permissions"]

        # login again
        login = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
        )
        assert login.status_code == 200, login.text

        # refresh rotates the token pair
        refreshed = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["access_token"]


@pytest.mark.asyncio
async def test_protected_route_requires_token() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/users/members")
    assert resp.status_code == 401
