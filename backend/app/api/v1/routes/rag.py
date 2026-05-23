"""RAG query endpoint — citation-grounded answer (non-streaming).

Streaming chat with conversation memory is added in Phase 5; this endpoint returns
a complete grounded answer with citations and a confidence score in one response.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentPrincipal, RagServiceDep, require_permission
from app.domains.identity.permissions import Permission
from app.domains.rag.schemas import RagAnswer, RagQuery

router = APIRouter()


@router.post(
    "/query",
    response_model=RagAnswer,
    dependencies=[Depends(require_permission(Permission.CHAT_WRITE))],
)
async def rag_query(query: RagQuery, principal: CurrentPrincipal, service: RagServiceDep) -> RagAnswer:
    assert principal.organization_id is not None
    return await service.answer(
        organization_id=principal.organization_id, user_id=principal.user_id, query=query
    )
