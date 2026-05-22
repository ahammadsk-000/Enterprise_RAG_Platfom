"""Ollama embedding provider (default).

Calls the Ollama HTTP API (`/api/embeddings`). Async via httpx; one request per text
(Ollama embeds a single prompt per call) gathered concurrently in bounded batches.
"""

from __future__ import annotations

import asyncio

import httpx

from app.core.config import LLMSettings
from app.core.exceptions import ProviderError


class OllamaEmbeddingProvider:
    provider = "ollama"

    def __init__(self, settings: LLMSettings, *, batch_size: int = 16) -> None:
        self.model_name = settings.embedding_model
        self.dim = settings.embedding_dim
        self.normalize = True
        self._base_url = settings.base_url.rstrip("/")
        self._timeout = settings.request_timeout_s
        self._batch_size = batch_size

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for start in range(0, len(texts), self._batch_size):
                batch = texts[start : start + self._batch_size]
                results.extend(await asyncio.gather(*(self._embed_one(client, t) for t in batch)))
        return results

    async def _embed_one(self, client: httpx.AsyncClient, text: str) -> list[float]:
        try:
            resp = await client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama embedding request failed: {exc}") from exc
        return resp.json()["embedding"]
