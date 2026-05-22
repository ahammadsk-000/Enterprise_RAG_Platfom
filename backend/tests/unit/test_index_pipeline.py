"""Unit test: full ingestion pipeline (PARSE→METADATA→CHUNK→INDEX) with fakes."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest

from app.domains.chunking.models.chunk import Chunk
from app.domains.chunking.services.chunking_service import ChunkingService
from app.domains.documents.enums import DocumentStatus
from app.domains.documents.models.document import Document
from app.domains.documents.models.ingestion_job import IngestionJob
from app.domains.embeddings.models.embedding_version import EmbeddingVersion
from app.domains.embeddings.services.embedding_service import EmbeddingService
from app.domains.ingestion.services.ingestion_service import IngestionService
from app.integrations.cache.embedding_cache import InMemoryEmbeddingCache
from app.integrations.embeddings.fake import FakeEmbeddingProvider
from app.integrations.ocr.base import NullOCREngine
from app.integrations.storage.memory import InMemoryObjectStorage
from app.integrations.vectorstore.factory import collection_name
from app.integrations.vectorstore.memory import InMemoryVectorStore


class _FakeSession:
    async def flush(self) -> None: ...
    async def commit(self) -> None: ...


class _FakeDocRepo:
    def __init__(self, document: Document) -> None:
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


class _FakeChunkRepo:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []

    async def add_all(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            if c.id is None:
                c.id = uuid.uuid4()
        self.chunks.extend(chunks)

    async def delete_for_document(self, document_id: uuid.UUID) -> None:
        self.chunks = [c for c in self.chunks if c.document_id != document_id]

    async def count_for_document(self, document_id: uuid.UUID) -> int:
        return sum(1 for c in self.chunks if c.document_id == document_id)

    async def list_for_document(self, document_id: uuid.UUID) -> Sequence[Chunk]:
        return [c for c in self.chunks if c.document_id == document_id]


class _FakeVersionRepo:
    async def get_or_create(self, *, provider: str, model_name: str, dim: int, normalize: bool) -> EmbeddingVersion:
        return EmbeddingVersion(
            id=uuid.uuid4(), provider=provider, model_name=model_name, dim=dim, normalize=normalize
        )


def _document() -> Document:
    return Document(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        title="doc.txt",
        storage_key="orgs/x/raw/abc",
        mime_type="text/plain",
        byte_size=10,
        content_hash="abc",
        status=DocumentStatus.UPLOADED.value,
        doc_metadata={},
    )


@pytest.mark.asyncio
async def test_full_pipeline_indexes_chunks_and_vectors() -> None:
    storage = InMemoryObjectStorage()
    doc = _document()
    body = "\n\n".join(f"Paragraph {i}: " + "knowledge " * 40 for i in range(6))
    await storage.put_object(doc.storage_key, body.encode(), "text/plain")

    chunk_repo = _FakeChunkRepo()
    vector_store = InMemoryVectorStore()
    provider = FakeEmbeddingProvider(dim=64)

    chunking = ChunkingService(_FakeSession(), chunk_repo)
    embedding = EmbeddingService(
        _FakeSession(), _FakeVersionRepo(), provider, vector_store, InMemoryEmbeddingCache()
    )
    service = IngestionService(
        _FakeSession(),
        _FakeDocRepo(doc),
        _FakeJobRepo(),
        storage,
        NullOCREngine(),
        chunking=chunking,
        embedding=embedding,
    )

    await service.run(doc.id)

    assert doc.status == DocumentStatus.INDEXED.value
    assert doc.doc_metadata["chunk_count"] > 0
    assert doc.doc_metadata["indexed_vectors"] == doc.doc_metadata["chunk_count"]

    # every chunk got an embedding version + vector id
    assert all(c.embedding_version_id is not None for c in chunk_repo.chunks)
    assert all(c.vector_id is not None for c in chunk_repo.chunks)

    # vectors are searchable in the tenant collection
    (query,) = await provider.embed_texts(["knowledge"])
    hits = await vector_store.search(collection_name(doc.organization_id), query, limit=3)
    assert hits
    assert hits[0].payload["document_id"] == str(doc.id)
