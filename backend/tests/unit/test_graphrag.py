"""Unit tests for Graph RAG: extractor, in-memory graph store, build + retrieval."""

from __future__ import annotations

import uuid

import pytest

from app.domains.graphrag.extractors.rule_based import RuleBasedExtractor
from app.domains.graphrag.services.graph_service import GraphBuilder, GraphRetrievalService
from app.integrations.graphstore.memory import InMemoryGraphStore


@pytest.mark.asyncio
async def test_rule_based_extractor_finds_entities_and_relations() -> None:
    result = await RuleBasedExtractor().extract("Paris is in France. Microsoft acquired GitHub.")
    names = {e.name for e in result.entities}
    assert "Paris" in names and "France" in names and "Microsoft" in names and "GitHub" in names
    assert any(r.source == "Microsoft" and r.target == "GitHub" for r in result.relations)


@pytest.mark.asyncio
async def test_graph_build_and_traverse() -> None:
    org = uuid.uuid4()
    doc = uuid.uuid4()
    store = InMemoryGraphStore()
    builder = GraphBuilder(RuleBasedExtractor(), store)

    count = await builder.build_from_text(
        organization_id=org, document_id=doc, text="Microsoft acquired GitHub. GitHub hosts Git repositories."
    )
    assert count >= 3

    retrieval = GraphRetrievalService(RuleBasedExtractor(), store)
    seeds, neighbors = await retrieval.related(organization_id=org, query="Tell me about Microsoft", hops=2)
    assert "Microsoft" in seeds
    neighbor_names = {n.name for n in neighbors}
    assert "GitHub" in neighbor_names  # 1-hop
    assert neighbor_names & {"Git", "Git repositories"}  # 2-hop reachable


@pytest.mark.asyncio
async def test_tenants_are_isolated() -> None:
    store = InMemoryGraphStore()
    builder = GraphBuilder(RuleBasedExtractor(), store)
    org_a, org_b = uuid.uuid4(), uuid.uuid4()
    await builder.build_from_text(organization_id=org_a, document_id=uuid.uuid4(), text="Acme builds Widgets.")

    retrieval = GraphRetrievalService(RuleBasedExtractor(), store)
    _, neighbors = await retrieval.related(organization_id=org_b, query="Acme", hops=1)
    assert neighbors == []  # org_b cannot see org_a's graph
