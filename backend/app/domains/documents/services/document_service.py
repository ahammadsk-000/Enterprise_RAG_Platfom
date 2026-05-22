"""Document use cases: upload (with dedupe), list, get, status, delete.

The service is tenant-scoped at the call site (organization_id comes from the
authenticated principal). Raw bytes are content-addressed in object storage; the
ingestion pipeline is triggered asynchronously via the task bus.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domains.chunking.repositories.chunk_repository import ChunkRepository
from app.domains.documents.enums import DocumentStatus
from app.domains.documents.models.document import Document
from app.domains.documents.models.ingestion_job import IngestionJob
from app.domains.documents.repositories.document_repository import DocumentRepository
from app.domains.documents.repositories.ingestion_job_repository import IngestionJobRepository
from app.domains.ingestion.parsers.registry import get_parser, guess_mime
from app.domains.ingestion.services.metadata import content_hash
from app.domains.ingestion.task_bus import TaskBus
from app.integrations.storage.base import ObjectStorage
from app.integrations.vectorstore.base import VectorStore
from app.integrations.vectorstore.factory import collection_name


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        documents: DocumentRepository,
        jobs: IngestionJobRepository,
        chunks: ChunkRepository,
        storage: ObjectStorage,
        vector_store: VectorStore,
        task_bus: TaskBus,
    ) -> None:
        self._session = session
        self._docs = documents
        self._jobs = jobs
        self._chunks = chunks
        self._storage = storage
        self._vectors = vector_store
        self._task_bus = task_bus

    async def upload(
        self,
        *,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        created_by: uuid.UUID | None,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> tuple[Document, bool]:
        """Store a file and enqueue ingestion. Returns (document, is_duplicate)."""
        mime = content_type or guess_mime(filename)
        get_parser(mime)  # validates the type early (raises ValidationError if unsupported)

        digest = content_hash(data)
        existing = await self._docs.find_duplicate(organization_id, digest)
        if existing is not None:
            return existing, True

        storage_key = f"orgs/{organization_id}/raw/{digest[:2]}/{digest}"
        await self._storage.put_object(storage_key, data, mime)

        document = await self._docs.add(
            Document(
                organization_id=organization_id,
                workspace_id=workspace_id,
                created_by=created_by,
                title=filename,
                storage_key=storage_key,
                mime_type=mime,
                byte_size=len(data),
                content_hash=digest,
                status=DocumentStatus.UPLOADED.value,
            )
        )
        await self._session.commit()
        self._task_bus.enqueue_ingestion(document.id)
        return document, False

    async def get(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> Document:
        document = await self._docs.get(document_id)
        if document is None or document.organization_id != organization_id:
            raise NotFoundError("Document not found.")
        return document

    async def list(
        self, organization_id: uuid.UUID, *, workspace_id: uuid.UUID | None, limit: int, offset: int
    ) -> tuple[Sequence[Document], int]:
        return await self._docs.list(
            organization_id, workspace_id=workspace_id, limit=limit, offset=offset
        )

    async def status(
        self, document_id: uuid.UUID, organization_id: uuid.UUID
    ) -> tuple[Document, Sequence[IngestionJob], int]:
        document = await self.get(document_id, organization_id)
        jobs = await self._jobs.list_for_document(document.id)
        chunk_count = await self._chunks.count_for_document(document.id)
        return document, jobs, chunk_count

    async def reindex(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> Document:
        """Re-run the ingestion pipeline (chunking is idempotent: old chunks are replaced)."""
        document = await self.get(document_id, organization_id)
        document.status = DocumentStatus.UPLOADED.value
        document.error = None
        await self._session.commit()
        self._task_bus.enqueue_ingestion(document.id)
        return document

    async def delete(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        document = await self.get(document_id, organization_id)
        # Remove vectors first (best-effort); chunk rows cascade with the document.
        await self._vectors.delete_by_document(collection_name(organization_id), document.id)
        await self._storage.delete_object(document.storage_key)
        if document.text_storage_key:
            await self._storage.delete_object(document.text_storage_key)
        await self._docs.delete(document)
        await self._session.commit()
