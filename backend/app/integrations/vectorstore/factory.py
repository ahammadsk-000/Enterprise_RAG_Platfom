"""Vector store selection + collection naming."""

from __future__ import annotations

import uuid
from functools import lru_cache

from app.core.config import get_settings
from app.integrations.vectorstore.base import VectorStore


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.environment == "test":
        from app.integrations.vectorstore.memory import InMemoryVectorStore

        return InMemoryVectorStore()

    from app.integrations.vectorstore.qdrant import QdrantVectorStore

    return QdrantVectorStore(settings.qdrant)


def collection_name(organization_id: uuid.UUID) -> str:
    """One collection per organization (tenant isolation at the collection level)."""
    prefix = get_settings().qdrant.collection_prefix
    return f"{prefix}_{organization_id.hex}"
