"""Graph store selection (test env → in-memory)."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.integrations.graphstore.base import GraphStore


@lru_cache(maxsize=1)
def get_graph_store() -> GraphStore:
    if get_settings().environment == "test":
        from app.integrations.graphstore.memory import InMemoryGraphStore

        return InMemoryGraphStore()

    from app.integrations.graphstore.neo4j import Neo4jGraphStore

    return Neo4jGraphStore(get_settings().neo4j)
