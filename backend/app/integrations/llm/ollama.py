"""Ollama chat LLM provider (default). Uses the /api/chat endpoint."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import LLMSettings
from app.core.exceptions import ProviderError
from app.integrations.llm.base import ChatMessage, LLMResult


class OllamaLLMProvider:
    provider = "ollama"

    def __init__(self, settings: LLMSettings) -> None:
        self.model_name = settings.chat_model
        self._base_url = settings.base_url.rstrip("/")
        self._timeout = settings.request_timeout_s

    def _payload(self, messages: list[ChatMessage], temperature: float, stream: bool) -> dict:
        return {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {"temperature": temperature},
        }

    async def generate(
        self, messages: list[ChatMessage], *, temperature: float = 0.0, max_tokens: int | None = None
    ) -> LLMResult:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/chat", json=self._payload(messages, temperature, False)
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama chat request failed: {exc}") from exc
        data = resp.json()
        return LLMResult(
            text=data["message"]["content"],
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            finish_reason=data.get("done_reason", "stop"),
        )

    async def stream(
        self, messages: list[ChatMessage], *, temperature: float = 0.0, max_tokens: int | None = None
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST", f"{self._base_url}/api/chat", json=self._payload(messages, temperature, True)
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if (token := chunk.get("message", {}).get("content")):
                        yield token
                    if chunk.get("done"):
                        break
