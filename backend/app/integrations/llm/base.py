"""LLM provider interface + value objects.

Phase 4 uses synchronous `generate`; token streaming (`stream`) is added in Phase 5
for the WebSocket chat. Providers are swappable via the factory (Ollama default).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["system", "user", "assistant"]


@dataclass(slots=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(slots=True)
class LLMResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMProvider(Protocol):
    provider: str
    model_name: str

    async def generate(
        self, messages: list[ChatMessage], *, temperature: float = 0.0, max_tokens: int | None = None
    ) -> LLMResult: ...

    def stream(
        self, messages: list[ChatMessage], *, temperature: float = 0.0, max_tokens: int | None = None
    ) -> AsyncIterator[str]: ...
