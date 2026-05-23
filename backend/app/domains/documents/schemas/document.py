"""Document DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.documents.enums import DocumentStatus, IngestionStage, JobStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID | None
    title: str
    mime_type: str
    byte_size: int
    content_hash: str
    status: DocumentStatus
    language: str | None
    page_count: int | None
    error: str | None
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int
    limit: int
    offset: int


class IngestionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage: IngestionStage
    status: JobStatus
    attempts: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: DocumentStatus
    chunk_count: int
    jobs: list[IngestionJobRead]


class UploadResponse(BaseModel):
    document: DocumentRead
    duplicate: bool = Field(default=False, description="True if an identical file already existed")


class DocumentContent(BaseModel):
    document_id: uuid.UUID
    title: str
    mime_type: str
    editable: bool
    content: str | None


class DocumentContentUpdate(BaseModel):
    content: str = Field(max_length=5_000_000)
