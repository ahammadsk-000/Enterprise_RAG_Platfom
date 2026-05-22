"""Celery ingestion task.

Thin wrapper: it builds an async session + the ingestion service and runs the
pipeline for one document. Retries with backoff on transient failures; the service
itself records per-stage job status and marks the document FAILED on hard errors.
"""

from __future__ import annotations

import asyncio
import uuid

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _run(document_id: uuid.UUID) -> None:
    from app.db.session import AsyncSessionLocal
    from app.domains.chunking.repositories.chunk_repository import SqlAlchemyChunkRepository
    from app.domains.chunking.services.chunking_service import ChunkingService
    from app.domains.documents.repositories.document_repository import SqlAlchemyDocumentRepository
    from app.domains.documents.repositories.ingestion_job_repository import (
        SqlAlchemyIngestionJobRepository,
    )
    from app.domains.embeddings.repositories.embedding_version_repository import (
        SqlAlchemyEmbeddingVersionRepository,
    )
    from app.domains.embeddings.services.embedding_service import EmbeddingService
    from app.domains.ingestion.services.ingestion_service import IngestionService
    from app.integrations.cache.embedding_cache import get_embedding_cache
    from app.integrations.embeddings.factory import get_embedding_provider
    from app.integrations.ocr.factory import get_ocr_engine
    from app.integrations.storage.factory import get_object_storage
    from app.integrations.vectorstore.factory import get_vector_store

    async with AsyncSessionLocal() as session:
        chunk_repo = SqlAlchemyChunkRepository(session)
        chunking = ChunkingService(session, chunk_repo)
        embedding = EmbeddingService(
            session=session,
            versions=SqlAlchemyEmbeddingVersionRepository(session),
            provider=get_embedding_provider(),
            vector_store=get_vector_store(),
            cache=get_embedding_cache(),
        )
        service = IngestionService(
            session=session,
            documents=SqlAlchemyDocumentRepository(session),
            jobs=SqlAlchemyIngestionJobRepository(session),
            storage=get_object_storage(),
            ocr=get_ocr_engine(),
            chunking=chunking,
            embedding=embedding,
        )
        await service.run(document_id)


@celery_app.task(
    name="app.workers.tasks.ingestion.ingest_document",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="parse",
)
def ingest_document(self, document_id: str) -> None:  # type: ignore[no-untyped-def]
    logger.info("ingestion.task.start", document_id=document_id)
    try:
        asyncio.run(_run(uuid.UUID(document_id)))
    except Exception as exc:  # noqa: BLE001 - retry transient infra errors
        logger.warning("ingestion.task.retry", document_id=document_id, error=str(exc))
        raise self.retry(exc=exc) from exc
