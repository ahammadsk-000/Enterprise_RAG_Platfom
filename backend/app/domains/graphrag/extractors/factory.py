"""Extractor selection (test env → deterministic rule-based)."""

from __future__ import annotations

from app.core.config import get_settings
from app.domains.graphrag.extractors.base import EntityExtractor


def get_entity_extractor() -> EntityExtractor:
    settings = get_settings()
    if settings.environment == "test" or settings.lite_mode:
        from app.domains.graphrag.extractors.rule_based import RuleBasedExtractor

        return RuleBasedExtractor()

    from app.domains.graphrag.extractors.llm import LLMEntityExtractor
    from app.integrations.llm.factory import get_llm_provider

    return LLMEntityExtractor(get_llm_provider())
