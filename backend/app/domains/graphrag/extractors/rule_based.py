"""Rule-based extractor (deterministic, dependency-free).

Treats capitalized multi-word spans as candidate entities and links entities that
co-occur within the same sentence with a generic RELATED_TO relation. Used in tests
and as a no-LLM fallback; the LLM extractor gives richer typed relations.
"""

from __future__ import annotations

import re

from app.domains.graphrag.extractors.base import ExtractionResult
from app.integrations.graphstore.base import GraphEntity, GraphRelation

_ENTITY_RE = re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = {"The", "A", "An", "This", "That", "These", "Those", "It", "He", "She", "They"}


class RuleBasedExtractor:
    async def extract(self, text: str) -> ExtractionResult:
        entities: dict[str, GraphEntity] = {}
        relations: list[GraphRelation] = []

        for sentence in _SENTENCE_RE.split(text):
            names = [
                m.group(1)
                for m in _ENTITY_RE.finditer(sentence)
                if m.group(1) not in _STOPWORDS and len(m.group(1)) > 2
            ]
            names = list(dict.fromkeys(names))  # de-dupe, keep order
            for name in names:
                entities.setdefault(name, GraphEntity(name=name, type="Entity"))
            for i, src in enumerate(names):
                for tgt in names[i + 1 :]:
                    relations.append(GraphRelation(source=src, target=tgt, type="RELATED_TO"))

        return ExtractionResult(entities=list(entities.values()), relations=relations)
