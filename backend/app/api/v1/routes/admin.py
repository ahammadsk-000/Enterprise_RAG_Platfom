"""Admin analytics endpoints (usage/cost/retrieval dashboards)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import AnalyticsServiceDep, CurrentPrincipal, require_permission
from app.domains.identity.permissions import Permission

router = APIRouter()


class AnalyticsOverview(BaseModel):
    documents_total: int
    documents_indexed: int
    conversations: int
    messages: int
    total_tokens: int
    avg_confidence: float | None
    retrieval_queries: int
    avg_retrieval_latency_ms: float | None
    agent_runs: int


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverview,
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
async def analytics_overview(principal: CurrentPrincipal, service: AnalyticsServiceDep) -> AnalyticsOverview:
    assert principal.organization_id is not None
    return AnalyticsOverview(**await service.overview(principal.organization_id))
