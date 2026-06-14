"""Graph store selection (test env → in-memory)."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.integrations.graphstore.base import GraphStore


@lru_cache(maxsize=1)
def get_graph_store() -> GraphStore:
    settings = get_settings()
    if settings.environment == "test" or settings.lite_mode:
        from app.integrations.graphstore.memory import InMemoryGraphStore

        return InMemoryGraphStore()

    from app.integrations.graphstore.neo4j import Neo4jGraphStore

    return Neo4jGraphStore(settings.neo4j)
