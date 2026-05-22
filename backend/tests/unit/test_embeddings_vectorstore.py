"""Unit tests for the fake embedding provider and in-memory vector store."""

from __future__ import annotations

import math
import uuid

import pytest

from app.integrations.embeddings.fake import FakeEmbeddingProvider
from app.integrations.vectorstore.base import VectorPoint
from app.integrations.vectorstore.memory import InMemoryVectorStore


@pytest.mark.asyncio
async def test_fake_provider_is_deterministic_and_normalized() -> None:
    provider = FakeEmbeddingProvider(dim=64)
    [v1], [v2] = await provider.embed_texts(["hello"]), await provider.embed_texts(["hello"])
    assert v1 == v2
    assert len(v1) == 64
    assert math.isclose(math.sqrt(sum(x * x for x in v1)), 1.0, rel_tol=1e-6)
    (other,) = await provider.embed_texts(["different text"])
    assert other != v1


@pytest.mark.asyncio
async def test_vector_store_upsert_search_filter_delete() -> None:
    store = InMemoryVectorStore()
    await store.ensure_collection("c1", dim=3)
    doc_a, doc_b = uuid.uuid4(), uuid.uuid4()
    p1 = VectorPoint(uuid.uuid4(), [1.0, 0.0, 0.0], {"document_id": str(doc_a)})
    p2 = VectorPoint(uuid.uuid4(), [0.0, 1.0, 0.0], {"document_id": str(doc_b)})
    await store.upsert("c1", [p1, p2])

    hits = await store.search("c1", [1.0, 0.0, 0.0], limit=2)
    assert hits[0].id == p1.id  # nearest by cosine

    filtered = await store.search("c1", [1.0, 1.0, 0.0], filters={"document_id": str(doc_b)})
    assert len(filtered) == 1 and filtered[0].id == p2.id

    await store.delete_by_document("c1", doc_a)
    remaining = await store.search("c1", [1.0, 0.0, 0.0], limit=5)
    assert all(h.id != p1.id for h in remaining)
