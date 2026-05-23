"""Entity/relation extraction contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.integrations.graphstore.base import GraphEntity, GraphRelation


@dataclass(slots=True)
class ExtractionResult:
    entities: list[GraphEntity] = field(default_factory=list)
    relations: list[GraphRelation] = field(default_factory=list)


class EntityExtractor(Protocol):
    async def extract(self, text: str) -> ExtractionResult: ...
