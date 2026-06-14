"""LLM provider selection (test env → deterministic fake)."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.integrations.llm.base import LLMProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.environment == "test" or settings.llm.provider == "fake":
        from app.integrations.llm.fake import FakeLLMProvider

        return FakeLLMProvider()

    if settings.llm.provider == "openai":
        from app.integrations.llm.openai import OpenAILLMProvider

        return OpenAILLMProvider(settings.llm)

    from app.integrations.llm.ollama import OllamaLLMProvider

    return OllamaLLMProvider(settings.llm)  # also serves vLLM via OpenAI-compatible if configured
