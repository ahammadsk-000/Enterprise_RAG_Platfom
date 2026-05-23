"""Graph store interface + value objects.

Implementations: `Neo4jGraphStore` (production) and `InMemoryGraphStore` (tests/dev).
The graph holds entities (nodes) and typed relations (edges) scoped per tenant; node
properties carry provenance back to source chunks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class GraphEntity:
    name: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphRelation:
    source: str
    target: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphNeighbor:
    name: str
    type: str
    relation: str
    direction: str  # out | in


class GraphStore(Protocol):
    async def upsert_entities(self, tenant: str, entities: list[GraphEntity]) -> None: ...
    async def upsert_relations(self, tenant: str, relations: list[GraphRelation]) -> None: ...
    async def neighbors(self, tenant: str, names: list[str], *, hops: int = 1, limit: int = 50) -> list[GraphNeighbor]: ...
    async def delete_document(self, tenant: str, document_id: str) -> None: ...
