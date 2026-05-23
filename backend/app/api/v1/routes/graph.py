"""Knowledge-graph exploration endpoint (Graph RAG)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import CurrentPrincipal, GraphRetrievalDep, require_permission
from app.domains.identity.permissions import Permission


class GraphExploreRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    hops: int = Field(default=1, ge=1, le=3)
    limit: int = Field(default=25, ge=1, le=100)


class GraphNeighborOut(BaseModel):
    name: str
    type: str
    relation: str
    direction: str


class GraphExploreResponse(BaseModel):
    seeds: list[str]
    neighbors: list[GraphNeighborOut]


router = APIRouter()


@router.post(
    "/explore",
    response_model=GraphExploreResponse,
    dependencies=[Depends(require_permission(Permission.SEARCH_READ))],
)
async def explore(req: GraphExploreRequest, principal: CurrentPrincipal, service: GraphRetrievalDep) -> GraphExploreResponse:
    """Find entities in the query and traverse their k-hop neighborhood in the graph."""
    assert principal.organization_id is not None
    seeds, neighbors = await service.related(
        organization_id=principal.organization_id, query=req.query, hops=req.hops, limit=req.limit
    )
    return GraphExploreResponse(
        seeds=seeds,
        neighbors=[
            GraphNeighborOut(name=n.name, type=n.type, relation=n.relation, direction=n.direction)
            for n in neighbors
        ],
    )
