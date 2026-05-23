"""Unit tests for the metrics endpoint + recording (no-op safe without prometheus)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.metrics import record_request, render_metrics
from app.main import create_app


def test_record_and_render_are_safe() -> None:
    # Must never raise, with or without prometheus_client installed.
    record_request("GET", "/api/v1/healthz", 200, 0.012)
    body, content_type = render_metrics()
    assert isinstance(body, bytes)
    assert content_type


@pytest.mark.asyncio
async def test_metrics_endpoint_exposed() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
