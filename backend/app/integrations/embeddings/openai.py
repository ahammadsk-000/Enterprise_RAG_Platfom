"""OpenAI-compatible embedding provider (also works with vLLM/LM-Studio gateways)."""

from __future__ import annotations

import httpx

from app.core.config import LLMSettings
from app.core.exceptions import ProviderError


class OpenAIEmbeddingProvider:
    provider = "openai"

    def __init__(self, settings: LLMSettings) -> None:
        self.model_name = settings.embedding_model
        self.dim = settings.embedding_dim
        self.normalize = False
        self._base_url = settings.base_url.rstrip("/")
        self._api_key = settings.api_key
        self._timeout = settings.request_timeout_s
        # Accept LLM_BASE_URL with or without "/v1" suffix (see openai.py chat provider).
        prefix = "" if self._base_url.endswith("/v1") else "/v1"
        self._embed_url = f"{self._base_url}{prefix}/embeddings"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._embed_url,
                    headers=headers,
                    json={"model": self.model_name, "input": texts},
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI embedding request failed: {exc}") from exc
        data = sorted(resp.json()["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in data]
