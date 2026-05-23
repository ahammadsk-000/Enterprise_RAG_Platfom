"""OpenAI-compatible chat provider (OpenAI, vLLM, LM-Studio, etc.)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import LLMSettings
from app.core.exceptions import ProviderError
from app.integrations.llm.base import ChatMessage, LLMResult


class OpenAILLMProvider:
    provider = "openai"

    def __init__(self, settings: LLMSettings) -> None:
        self.model_name = settings.chat_model
        self._base_url = settings.base_url.rstrip("/")
        self._api_key = settings.api_key
        self._timeout = settings.request_timeout_s

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

    def _payload(self, messages: list[ChatMessage], temperature: float, max_tokens: int | None, stream: bool) -> dict:
        body: dict = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        return body

    async def generate(
        self, messages: list[ChatMessage], *, temperature: float = 0.0, max_tokens: int | None = None
    ) -> LLMResult:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    headers=self._headers(),
                    json=self._payload(messages, temperature, max_tokens, False),
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI chat request failed: {exc}") from exc
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResult(
            text=choice["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def stream(
        self, messages: list[ChatMessage], *, temperature: float = 0.0, max_tokens: int | None = None
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, temperature, max_tokens, True),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        break
                    delta = json.loads(payload)["choices"][0].get("delta", {})
                    if (token := delta.get("content")):
                        yield token
