"""Retrieval DTOs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, Field


class RetrievalStrategy(StrEnum):
    DENSE = "dense"
    BM25 = "bm25"
    HYBRID = "hybrid"


@dataclass(slots=True)
class RetrievedChunk:
    """A retrieved chunk with provenance + score (internal pipeline type)."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    source: str = "dense"  # dense | bm25 | hybrid
    page_from: int | None = None
    page_to: int | None = None
    chunk_type: str = "text"
    metadata: dict = field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=10, ge=1, le=50)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    rerank: bool = True
    workspace_id: uuid.UUID | None = None


class SearchHitOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    source: str
    page_from: int | None
    chunk_type: str


class SearchResponse(BaseModel):
    query: str
    strategy: RetrievalStrategy
    hits: list[SearchHitOut]
    latency_ms: float
