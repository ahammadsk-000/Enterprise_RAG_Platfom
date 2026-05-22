"""Liveness and readiness endpoints.

- `/healthz` — liveness: process is up (no dependencies checked).
- `/readyz`  — readiness: critical dependencies (DB) are reachable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "service": settings.telemetry.service_name, "env": settings.environment}


@router.get("/readyz", summary="Readiness probe")
async def readyz(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    from fastapi import HTTPException

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - exercised in integration tests
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unavailable: {exc}",
        ) from exc
    return {"status": "ready"}
