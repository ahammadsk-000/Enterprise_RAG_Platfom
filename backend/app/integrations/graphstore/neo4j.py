"""Neo4j graph store (lazy async driver).

Entities are `(:Entity {tenant, name, type})`; relations are `[:REL {type, ...}]`.
A composite tenant+name key keeps graphs isolated per organization. The neo4j
driver is imported lazily so the module loads without the dependency.
"""

from __future__ import annotations

from app.core.config import Neo4jSettings
from app.core.exceptions import ProviderError
from app.integrations.graphstore.base import GraphEntity, GraphNeighbor, GraphRelation


class Neo4jGraphStore:
    def __init__(self, settings: Neo4jSettings) -> None:
        self._driver = self._build_driver(settings)

    @staticmethod
    def _build_driver(settings: Neo4jSettings):  # type: ignore[no-untyped-def]
        try:
            from neo4j import AsyncGraphDatabase  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError("neo4j driver is not installed.") from exc
        return AsyncGraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))

    async def upsert_entities(self, tenant: str, entities: list[GraphEntity]) -> None:
        query = (
            "UNWIND $rows AS row "
            "MERGE (e:Entity {tenant: $tenant, name: row.name}) "
            "SET e.type = row.type, e += row.props"
        )
        rows = [{"name": e.name, "type": e.type, "props": e.properties} for e in entities]
        async with self._driver.session() as session:
            await session.run(query, tenant=tenant, rows=rows)

    async def upsert_relations(self, tenant: str, relations: list[GraphRelation]) -> None:
        query = (
            "UNWIND $rows AS row "
            "MERGE (a:Entity {tenant: $tenant, name: row.source}) "
            "MERGE (b:Entity {tenant: $tenant, name: row.target}) "
            "MERGE (a)-[r:REL {type: row.type}]->(b) SET r += row.props"
        )
        rows = [{"source": r.source, "target": r.target, "type": r.type, "props": r.properties} for r in relations]
        async with self._driver.session() as session:
            await session.run(query, tenant=tenant, rows=rows)

    async def neighbors(
        self, tenant: str, names: list[str], *, hops: int = 1, limit: int = 50
    ) -> list[GraphNeighbor]:
        query = (
            f"MATCH (e:Entity {{tenant: $tenant}}) WHERE toLower(e.name) IN $names "
            f"MATCH (e)-[r:REL*1..{max(1, hops)}]-(n:Entity) "
            "RETURN DISTINCT n.name AS name, n.type AS type, "
            "last(r).type AS relation LIMIT $limit"
        )
        async with self._driver.session() as session:
            result = await session.run(
                query, tenant=tenant, names=[n.lower() for n in names], limit=limit
            )
            records = await result.data()
        return [
            GraphNeighbor(rec["name"], rec.get("type") or "Entity", rec.get("relation") or "REL", "out")
            for rec in records
        ]

    async def delete_document(self, tenant: str, document_id: str) -> None:
        query = "MATCH (:Entity {tenant: $tenant})-[r:REL {document_id: $doc}]-() DELETE r"
        async with self._driver.session() as session:
            await session.run(query, tenant=tenant, doc=document_id)
