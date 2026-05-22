"""Deterministic fake embedding provider for tests and offline development.

Hashes text into a stable pseudo-random unit vector. No network, no model — but
identical text always yields the identical vector, so similarity is meaningful.
"""

from __future__ import annotations

import hashlib
import math


class FakeEmbeddingProvider:
    provider = "fake"
    model_name = "fake-embed"

    def __init__(self, dim: int = 64, normalize: bool = True) -> None:
        self.dim = dim
        self.normalize = normalize

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> list[float]:
        vec: list[float] = []
        counter = 0
        while len(vec) < self.dim:
            digest = hashlib.sha256(f"{text}:{counter}".encode()).digest()
            vec.extend(b / 255.0 - 0.5 for b in digest)
            counter += 1
        vec = vec[: self.dim]
        if self.normalize:
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            vec = [x / norm for x in vec]
        return vec
