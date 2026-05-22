"""Embedding provider interface.

Implementations embed batches of text into fixed-dimension vectors. `model_name`,
`dim`, and `provider` identify the embedding version used to index a corpus.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    provider: str
    model_name: str
    dim: int
    normalize: bool

    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
