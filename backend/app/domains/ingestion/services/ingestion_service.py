"""Ingestion pipeline orchestrator (runs inside the Celery worker).

Stages for Phase 2: PARSE (text extraction + OCR fallback) and METADATA (language,
counts, text-artifact persistence). Each stage is recorded as an `IngestionJob`.
CHUNK/EMBED/INDEX stages are appended in Phases 3–4.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domains.documents.enums import DocumentStatus, IngestionStage, JobStatus
from app.domains.documents.models.document import Document
from app.domains.documents.models.ingestion_job import IngestionJob
from app.domains.documents.repositories.document_repository import DocumentRepository
from app.domains.documents.repositories.ingestion_job_repository import IngestionJobRepository
from app.domains.ingestion.parsers.base import ParsedDocument
from app.domains.ingestion.parsers.registry import get_parser
from app.domains.ingestion.services.metadata import derive_metadata, detect_language
from app.integrations.ocr.base import OCREngine
from app.integrations.storage.base import ObjectStorage

logger = get_logger(__name__)

T = TypeVar("T")


class IngestionService:
    def __init__(
        self,
        session: AsyncSession,
        documents: DocumentRepository,
        jobs: IngestionJobRepository,
        storage: ObjectStorage,
        ocr: OCREngine,
    ) -> None:
        self._session = session
        self._docs = documents
        self._jobs = jobs
        self._storage = storage
        self._ocr = ocr

    async def run(self, document_id: uuid.UUID) -> None:
        document = await self._docs.get(document_id)
        if document is None:
            logger.warning("ingestion.document_missing", document_id=str(document_id))
            return

        document.status = DocumentStatus.PARSING.value
        document.error = None
        await self._session.flush()

        try:
            parsed = await self._run_stage(
                document, IngestionStage.PARSE, lambda: self._parse(document)
            )
            await self._run_stage(
                document, IngestionStage.METADATA, lambda: self._extract_metadata(document, parsed)
            )
            document.status = DocumentStatus.PARSED.value
            logger.info("ingestion.completed", document_id=str(document_id), pages=document.page_count)
        except Exception as exc:  # noqa: BLE001 - any stage failure marks the doc FAILED
            document.status = DocumentStatus.FAILED.value
            document.error = str(exc)
            logger.exception("ingestion.failed", document_id=str(document_id))

        await self._session.commit()

    # ── Stages ──────────────────────────────────────────────────────────────
    async def _parse(self, document: Document) -> ParsedDocument:
        data = await self._storage.get_object(document.storage_key)
        parser = get_parser(document.mime_type)
        return await parser.parse(data, filename=document.title, ocr=self._ocr)

    async def _extract_metadata(self, document: Document, parsed: ParsedDocument) -> None:
        text_key = f"orgs/{document.organization_id}/text/{document.content_hash}.txt"
        await self._storage.put_object(text_key, parsed.text.encode("utf-8"), "text/plain")
        document.text_storage_key = text_key
        document.page_count = parsed.page_count
        document.language = detect_language(parsed.text)
        document.doc_metadata = {**document.doc_metadata, **derive_metadata(parsed)}

    # ── Job bookkeeping ───────────────────────────────────────────────────────
    async def _run_stage(
        self, document: Document, stage: IngestionStage, work: Callable[[], Awaitable[T]]
    ) -> T:
        job = await self._jobs.add(
            IngestionJob(
                document_id=document.id,
                stage=stage.value,
                status=JobStatus.RUNNING.value,
                attempts=1,
                started_at=datetime.now(UTC),
            )
        )
        try:
            result = await work()
        except Exception as exc:
            job.status = JobStatus.FAILED.value
            job.error = str(exc)
            job.finished_at = datetime.now(UTC)
            await self._session.flush()
            raise
        job.status = JobStatus.SUCCEEDED.value
        job.finished_at = datetime.now(UTC)
        await self._session.flush()
        return result
