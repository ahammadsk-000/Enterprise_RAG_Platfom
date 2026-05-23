"""Agentic retrieval endpoint (multi-agent research workflow)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import AgentServiceDep, CurrentPrincipal, require_permission
from app.domains.agents.schemas import AgentResearchRequest, AgentResearchResponse
from app.domains.identity.permissions import Permission

router = APIRouter()


@router.post(
    "/research",
    response_model=AgentResearchResponse,
    dependencies=[Depends(require_permission(Permission.AGENTS_RUN))],
)
async def research(
    req: AgentResearchRequest, principal: CurrentPrincipal, service: AgentServiceDep
) -> AgentResearchResponse:
    """Run the planner→retriever→summarizer→verifier→citation agent graph."""
    assert principal.organization_id is not None
    return await service.research(organization_id=principal.organization_id, user_id=principal.user_id, req=req)
