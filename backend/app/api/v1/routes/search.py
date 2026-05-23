"""Hybrid search endpoint (retrieval only, no generation)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentPrincipal, RetrievalServiceDep, require_permission
from app.domains.identity.permissions import Permission
from app.domains.retrieval.schemas import SearchHitOut, SearchRequest, SearchResponse

router = APIRouter()


@router.post(
    "",
    response_model=SearchResponse,
    dependencies=[Depends(require_permission(Permission.SEARCH_READ))],
)
async def search(
    request: SearchRequest, principal: CurrentPrincipal, service: RetrievalServiceDep
) -> SearchResponse:
    """Run dense + BM25 hybrid retrieval and return ranked chunks with provenance."""
    assert principal.organization_id is not None
    hits, latency_ms = await service.search(
        organization_id=principal.organization_id,
        workspace_id=request.workspace_id,
        query=request.query,
        top_k=request.top_k,
        strategy=request.strategy,
        rerank=request.rerank,
        user_id=principal.user_id,
    )
    return SearchResponse(
        query=request.query,
        strategy=request.strategy,
        latency_ms=latency_ms,
        hits=[
            SearchHitOut(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                content=h.content,
                score=h.score,
                source=h.source,
                page_from=h.page_from,
                chunk_type=h.chunk_type,
            )
            for h in hits
        ],
    )
