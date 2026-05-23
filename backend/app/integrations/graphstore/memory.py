"""In-memory graph store (tests/dev) — adjacency over entities + typed relations."""

from __future__ import annotations

from collections import defaultdict

from app.integrations.graphstore.base import GraphEntity, GraphNeighbor, GraphRelation


class InMemoryGraphStore:
    def __init__(self) -> None:
        # tenant -> entity name -> type
        self._entities: dict[str, dict[str, str]] = defaultdict(dict)
        # tenant -> list of relations
        self._relations: dict[str, list[GraphRelation]] = defaultdict(list)

    async def upsert_entities(self, tenant: str, entities: list[GraphEntity]) -> None:
        for e in entities:
            self._entities[tenant][e.name.lower()] = e.type

    async def upsert_relations(self, tenant: str, relations: list[GraphRelation]) -> None:
        self._relations[tenant].extend(relations)

    async def neighbors(
        self, tenant: str, names: list[str], *, hops: int = 1, limit: int = 50
    ) -> list[GraphNeighbor]:
        wanted = {n.lower() for n in names}
        frontier = set(wanted)
        seen: set[str] = set(wanted)
        out: list[GraphNeighbor] = []
        for _ in range(hops):
            next_frontier: set[str] = set()
            for rel in self._relations[tenant]:
                s, t = rel.source.lower(), rel.target.lower()
                if s in frontier and t not in seen:
                    out.append(GraphNeighbor(rel.target, self._entities[tenant].get(t, "Entity"), rel.type, "out"))
                    next_frontier.add(t)
                elif t in frontier and s not in seen:
                    out.append(GraphNeighbor(rel.source, self._entities[tenant].get(s, "Entity"), rel.type, "in"))
                    next_frontier.add(s)
            seen |= next_frontier
            frontier = next_frontier
            if not frontier:
                break
        return out[:limit]

    async def delete_document(self, tenant: str, document_id: str) -> None:
        self._relations[tenant] = [
            r for r in self._relations[tenant] if r.properties.get("document_id") != document_id
        ]
