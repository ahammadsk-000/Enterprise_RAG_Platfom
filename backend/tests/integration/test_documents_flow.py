"""Document API flow against real Postgres (`pytest -m integration`, ENVIRONMENT=test).

ENVIRONMENT=test selects in-memory object storage; the task bus is overridden with a
NullTaskBus so no worker is required. The async pipeline itself is covered by the
unit test in tests/unit/test_ingestion_pipeline.py.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_task_bus
from app.domains.ingestion.task_bus import NullTaskBus
from app.main import create_app

pytestmark = pytest.mark.integration


async def _auth_client(app) -> tuple[AsyncClient, dict[str, str]]:  # type: ignore[no-untyped-def]
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    email = f"docs-{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "DocCo"},
    )
    token = reg.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_upload_dedupe_list_get_delete() -> None:
    app = create_app()
    app.dependency_overrides[get_task_bus] = lambda: NullTaskBus()
    client, headers = await _auth_client(app)

    files = {"file": ("notes.txt", b"hello enterprise rag", "text/plain")}
    up = await client.post("/api/v1/documents", files=files, headers=headers)
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["duplicate"] is False
    assert body["document"]["status"] == "uploaded"
    doc_id = body["document"]["id"]

    # identical content → duplicate detected
    dup = await client.post("/api/v1/documents", files=files, headers=headers)
    assert dup.json()["duplicate"] is True

    listing = await client.get("/api/v1/documents", headers=headers)
    assert listing.json()["total"] >= 1

    got = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert got.status_code == 200

    status_resp = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_resp.status_code == 200

    deleted = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert deleted.status_code == 204
    await client.aclose()


@pytest.mark.asyncio
async def test_unsupported_type_rejected() -> None:
    app = create_app()
    app.dependency_overrides[get_task_bus] = lambda: NullTaskBus()
    client, headers = await _auth_client(app)
    files = {"file": ("x.bin", b"\x00\x01\x02", "application/x-totally-unknown")}
    resp = await client.post("/api/v1/documents", files=files, headers=headers)
    assert resp.status_code == 422
    await client.aclose()
