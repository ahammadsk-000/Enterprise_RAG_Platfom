"""Agent DTOs."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.domains.rag.schemas import Citation


class AgentResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=6, ge=1, le=20)
    workspace_id: uuid.UUID | None = None


class AgentStepOut(BaseModel):
    node: str
    role: str
    output: dict
    latency_ms: float


class AgentResearchResponse(BaseModel):
    run_id: uuid.UUID | None
    answer: str
    citations: list[Citation]
    confidence: float
    verified: bool
    sub_questions: list[str]
    steps: list[AgentStepOut]
    total_tokens: int
