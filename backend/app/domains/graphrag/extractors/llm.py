"""LLM-based entity/relation extractor (JSON-structured output).

Prompts the chat model to emit typed entities + relations as JSON; falls back to the
rule-based extractor if the model output can't be parsed.
"""

from __future__ import annotations

import json
import re

from app.core.logging import get_logger
from app.domains.graphrag.extractors.base import ExtractionResult
from app.domains.graphrag.extractors.rule_based import RuleBasedExtractor
from app.integrations.graphstore.base import GraphEntity, GraphRelation
from app.integrations.llm.base import ChatMessage, LLMProvider

logger = get_logger(__name__)

_PROMPT = (
    "Extract a knowledge graph from the text. Return STRICT JSON with keys "
    '"entities" (list of {"name","type"}) and "relations" '
    '(list of {"source","target","type"}). Types are short labels (Person, '
    "Organization, Concept, Location, etc.). Text:\n\n{text}"
)
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMEntityExtractor:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._fallback = RuleBasedExtractor()

    async def extract(self, text: str) -> ExtractionResult:
        result = await self._llm.generate(
            [ChatMessage(role="user", content=_PROMPT.format(text=text[:6000]))], temperature=0.0
        )
        match = _JSON_RE.search(result.text)
        if not match:
            logger.warning("graph.extract.unparsable_output")
            return await self._fallback.extract(text)
        try:
            data = json.loads(match.group(0))
            entities = [GraphEntity(name=e["name"], type=e.get("type", "Entity")) for e in data.get("entities", [])]
            relations = [
                GraphRelation(source=r["source"], target=r["target"], type=r.get("type", "RELATED_TO"))
                for r in data.get("relations", [])
            ]
            return ExtractionResult(entities=entities, relations=relations)
        except (json.JSONDecodeError, KeyError, TypeError):
            return await self._fallback.extract(text)
