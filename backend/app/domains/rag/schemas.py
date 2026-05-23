"""RAG DTOs: query, citation, and grounded answer."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.domains.retrieval.schemas import RetrievalStrategy


class RagQuery(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=6, ge=1, le=20)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    rerank: bool = True
    workspace_id: uuid.UUID | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class Citation(BaseModel):
    marker: int = Field(description="1-based index referenced as [n] in the answer")
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    page_from: int | None = None
    snippet: str
    score: float


class RagAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float = Field(ge=0.0, le=1.0)
    model: str
    strategy: RetrievalStrategy
    retrieved: int
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
