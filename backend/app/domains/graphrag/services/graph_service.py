"""Graph build + graph-augmented retrieval.

`GraphBuilder` extracts entities/relations from a document's text and upserts them
into the tenant's graph (with document_id provenance). `GraphRetrievalService`
expands a query into related entities via k-hop traversal — used standalone (graph
explore) and to enrich vector retrieval (hybrid graph/vector).
"""

from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.domains.graphrag.extractors.base import EntityExtractor
from app.integrations.graphstore.base import GraphNeighbor, GraphStore

logger = get_logger(__name__)


def _tenant(organization_id: uuid.UUID) -> str:
    return organization_id.hex


class GraphBuilder:
    def __init__(self, extractor: EntityExtractor, graph: GraphStore) -> None:
        self._extractor = extractor
        self._graph = graph

    async def build_from_text(self, *, organization_id: uuid.UUID, document_id: uuid.UUID, text: str) -> int:
        result = await self._extractor.extract(text)
        if not result.entities:
            return 0
        tenant = _tenant(organization_id)
        for rel in result.relations:
            rel.properties["document_id"] = str(document_id)
        await self._graph.upsert_entities(tenant, result.entities)
        await self._graph.upsert_relations(tenant, result.relations)
        logger.info(
            "graph.built", document_id=str(document_id),
            entities=len(result.entities), relations=len(result.relations),
        )
        return len(result.entities)


class GraphRetrievalService:
    def __init__(self, extractor: EntityExtractor, graph: GraphStore) -> None:
        self._extractor = extractor
        self._graph = graph

    async def related(
        self, *, organization_id: uuid.UUID, query: str, hops: int = 1, limit: int = 25
    ) -> tuple[list[str], list[GraphNeighbor]]:
        """Return (seed entities found in the query, their graph neighbors)."""
        extraction = await self._extractor.extract(query)
        seeds = [e.name for e in extraction.entities]
        if not seeds:
            return [], []
        neighbors = await self._graph.neighbors(_tenant(organization_id), seeds, hops=hops, limit=limit)
        return seeds, neighbors

    async def expansion_terms(self, *, organization_id: uuid.UUID, query: str, limit: int = 10) -> list[str]:
        """Neighbor entity names to widen a vector/keyword query (hybrid graph+vector)."""
        _, neighbors = await self.related(organization_id=organization_id, query=query, limit=limit)
        return list(dict.fromkeys(n.name for n in neighbors))
