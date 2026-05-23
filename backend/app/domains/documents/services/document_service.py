"""Document use cases: upload (with dedupe), list, get, status, delete.

The service is tenant-scoped at the call site (organization_id comes from the
authenticated principal). Raw bytes are content-addressed in object storage; the
ingestion pipeline is triggered asynchronously via the task bus.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
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

# Text-based types that can be edited in-browser (binary docs are download-only).
_EDITABLE_MIMES = {
    "application/json",
    "application/xml",
    "application/csv",
    "application/x-yaml",
}


def is_editable(mime_type: str) -> bool:
    return mime_type.startswith("text/") or mime_type in _EDITABLE_MIMES


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

    async def get_content(
        self, document_id: uuid.UUID, organization_id: uuid.UUID
    ) -> tuple[Document, str | None, bool]:
        """Return (document, decoded text or None, editable). Binary files are not editable."""
        document = await self.get(document_id, organization_id)
        editable = is_editable(document.mime_type)
        text: str | None = None
        if editable:
            data = await self._storage.get_object(document.storage_key)
            text = data.decode("utf-8", errors="replace")
        return document, text, editable

    async def read_bytes(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> tuple[Document, bytes]:
        """Return (document, raw stored bytes) for download."""
        document = await self.get(document_id, organization_id)
        return document, await self._storage.get_object(document.storage_key)

    async def extract_to_markdown(
        self, document_id: uuid.UUID, organization_id: uuid.UUID, created_by: uuid.UUID | None
    ) -> tuple[Document, bool]:
        """Create an editable .md document from a binary doc's extracted text.

        The original is left untouched (still downloadable). Returns (document, created);
        `created` is False when an identical extraction already exists. Useful for
        PDF/DOCX, which can't be edited in place but whose text can be edited + re-indexed.
        """
        source = await self.get(document_id, organization_id)
        if not source.text_storage_key:
            raise ValidationError("No extracted text yet — wait for ingestion to finish, then retry.")

        text_bytes = await self._storage.get_object(source.text_storage_key)
        digest = content_hash(text_bytes)
        existing = await self._docs.find_duplicate(organization_id, digest)
        if existing is not None:
            return existing, False

        stem = source.title.rsplit(".", 1)[0] if "." in source.title else source.title
        storage_key = f"orgs/{organization_id}/raw/{digest[:2]}/{digest}"
        await self._storage.put_object(storage_key, text_bytes, "text/markdown")

        document = await self._docs.add(
            Document(
                organization_id=organization_id,
                workspace_id=source.workspace_id,
                created_by=created_by,
                title=f"{stem}.md",
                storage_key=storage_key,
                mime_type="text/markdown",
                byte_size=len(text_bytes),
                content_hash=digest,
                status=DocumentStatus.UPLOADED.value,
                doc_metadata={"extracted_from": str(source.id)},
            )
        )
        await self._session.commit()
        self._task_bus.enqueue_ingestion(document.id)
        return document, True

    async def update_content(
        self, document_id: uuid.UUID, organization_id: uuid.UUID, content: str
    ) -> Document:
        """Save edited text: store new bytes, drop stale vectors, and re-run ingestion."""
        document = await self.get(document_id, organization_id)
        if not is_editable(document.mime_type):
            raise ValidationError("This file type is not editable.")

        new_bytes = content.encode("utf-8")
        new_hash = content_hash(new_bytes)
        if new_hash == document.content_hash:
            return document  # no change → no reindex

        new_key = f"orgs/{organization_id}/raw/{new_hash[:2]}/{new_hash}"
        await self._storage.put_object(new_key, new_bytes, document.mime_type)
        old_key = document.storage_key

        document.storage_key = new_key
        document.content_hash = new_hash
        document.byte_size = len(new_bytes)
        document.status = DocumentStatus.UPLOADED.value
        document.error = None
        await self._session.commit()

        # Best-effort cleanup of the previous object + stale vectors, then re-ingest.
        await self._storage.delete_object(old_key)
        await self._vectors.delete_by_document(collection_name(organization_id), document.id)
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
