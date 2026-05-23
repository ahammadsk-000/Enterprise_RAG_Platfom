"""Chat DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.rag.schemas import Citation
from app.domains.retrieval.schemas import RetrievalStrategy


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=512)
    workspace_id: uuid.UUID | None = None
    system_prompt: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    workspace_id: uuid.UUID | None
    last_message_at: datetime | None
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    model: str | None
    confidence: float | None
    citations: list
    created_at: datetime


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=6, ge=1, le=20)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    rerank: bool = True
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    message_id: uuid.UUID
    answer: str
    citations: list[Citation]
    confidence: float
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
