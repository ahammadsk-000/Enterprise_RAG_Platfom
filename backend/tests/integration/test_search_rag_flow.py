"""End-to-end retrieval + RAG flow (`pytest -m integration`, ENVIRONMENT=test).

Requires Postgres (BM25 uses full-text search). ENVIRONMENT=test selects in-memory
storage / vector store and the deterministic fake embedding + LLM providers, all of
which are process-cached singletons — so the inline ingestion step and the API share
the same vector store, making a true upload→index→search→answer path testable.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_task_bus
from app.domains.ingestion.task_bus import NullTaskBus
from app.main import create_app
from app.workers.tasks.ingestion import run_ingestion_pipeline as run_ingestion

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_upload_index_search_and_rag() -> None:
    app = create_app()
    app.dependency_overrides[get_task_bus] = lambda: NullTaskBus()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    email = f"rag-{uuid.uuid4().hex[:8]}@example.com"

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "RagCo"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    body = b"Paris is the capital of France. The Eiffel Tower is located in Paris."
    up = await client.post(
        "/api/v1/documents", files={"file": ("geo.txt", body, "text/plain")}, headers=headers
    )
    doc_id = uuid.UUID(up.json()["document"]["id"])

    # Run the real ingestion pipeline inline (chunk → embed → index into the shared store).
    await run_ingestion(doc_id)

    status = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status.json()["status"] == "indexed"
    assert status.json()["chunk_count"] >= 1

    search = await client.post(
        "/api/v1/search", json={"query": "capital of France", "top_k": 5}, headers=headers
    )
    assert search.status_code == 200, search.text
    assert len(search.json()["hits"]) >= 1

    rag = await client.post(
        "/api/v1/rag/query", json={"query": "What is the capital of France?", "top_k": 5}, headers=headers
    )
    assert rag.status_code == 200, rag.text
    payload = rag.json()
    assert payload["citations"]
    assert payload["retrieved"] >= 1
    assert 0.0 <= payload["confidence"] <= 1.0
    await client.aclose()
