"""Unit test for the ingestion orchestrator using fakes (no database).

Exercises the full PARSE → METADATA flow and the failure path, asserting status
transitions, job recording, and text-artifact persistence.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest

from app.domains.documents.enums import DocumentStatus, JobStatus
from app.domains.documents.models.document import Document
from app.domains.documents.models.ingestion_job import IngestionJob
from app.domains.ingestion.services.ingestion_service import IngestionService
from app.integrations.ocr.base import NullOCREngine
from app.integrations.storage.memory import InMemoryObjectStorage


class _FakeSession:
    async def flush(self) -> None: ...
    async def commit(self) -> None: ...


class _FakeDocRepo:
    def __init__(self, document: Document | None) -> None:
        self._document = document

    async def get(self, document_id: uuid.UUID) -> Document | None:
        return self._document


class _FakeJobRepo:
    def __init__(self) -> None:
        self.jobs: list[IngestionJob] = []

    async def add(self, job: IngestionJob) -> IngestionJob:
        self.jobs.append(job)
        return job

    async def list_for_document(self, document_id: uuid.UUID) -> Sequence[IngestionJob]:
        return self.jobs


def _document(storage_key: str) -> Document:
    return Document(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        title="notes.txt",
        storage_key=storage_key,
        mime_type="text/plain",
        byte_size=42,
        content_hash="deadbeef",
        status=DocumentStatus.UPLOADED.value,
        doc_metadata={},
    )


@pytest.mark.asyncio
async def test_pipeline_parses_and_marks_parsed() -> None:
    storage = InMemoryObjectStorage()
    doc = _document("orgs/x/raw/deadbeef")
    await storage.put_object(doc.storage_key, b"The quick brown fox jumps over the lazy dog.", "text/plain")

    jobs = _FakeJobRepo()
    service = IngestionService(_FakeSession(), _FakeDocRepo(doc), jobs, storage, NullOCREngine())
    await service.run(doc.id)

    assert doc.status == DocumentStatus.PARSED.value
    assert doc.page_count == 1
    assert doc.text_storage_key is not None
    assert doc.doc_metadata["word_count"] == 9
    # PARSE + METADATA stages both recorded and succeeded
    assert len(jobs.jobs) == 2
    assert all(j.status == JobStatus.SUCCEEDED.value for j in jobs.jobs)
    # text artifact persisted
    assert b"quick brown fox" in await storage.get_object(doc.text_storage_key)


@pytest.mark.asyncio
async def test_pipeline_marks_failed_when_object_missing() -> None:
    storage = InMemoryObjectStorage()  # raw object intentionally absent
    doc = _document("orgs/x/raw/missing")

    jobs = _FakeJobRepo()
    service = IngestionService(_FakeSession(), _FakeDocRepo(doc), jobs, storage, NullOCREngine())
    await service.run(doc.id)

    assert doc.status == DocumentStatus.FAILED.value
    assert doc.error
    assert jobs.jobs[0].status == JobStatus.FAILED.value
