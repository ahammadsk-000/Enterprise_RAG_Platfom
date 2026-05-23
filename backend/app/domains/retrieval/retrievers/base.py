"""First-stage retriever interface."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.domains.retrieval.schemas import RetrievedChunk


class Retriever(Protocol):
    async def retrieve(
        self,
        *,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]: ...
