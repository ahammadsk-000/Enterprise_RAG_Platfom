"""Deterministic fake LLM for tests/offline dev.

Produces a grounded-looking answer that cites the first context item as ``[1]`` so
the citation engine has something to resolve, and streams it token-by-token.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.integrations.llm.base import ChatMessage, LLMResult


class FakeLLMProvider:
    provider = "fake"
    model_name = "fake-llm"

    async def generate(
        self, messages: list[ChatMessage], *, temperature: float = 0.0, max_tokens: int | None = None
    ) -> LLMResult:
        text = self._answer(messages)
        return LLMResult(text=text, prompt_tokens=len(messages), completion_tokens=len(text.split()))

    async def stream(
        self, messages: list[ChatMessage], *, temperature: float = 0.0, max_tokens: int | None = None
    ) -> AsyncIterator[str]:
        for token in self._answer(messages).split(" "):
            yield token + " "

    @staticmethod
    def _answer(messages: list[ChatMessage]) -> str:
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        topic = user.splitlines()[0][:80] if user else "your question"
        return f"Based on the provided sources, here is the answer to {topic} [1]."
