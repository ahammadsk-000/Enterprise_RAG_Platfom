"""Re-ranker selection (test env → null reranker)."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.integrations.reranker.base import Reranker


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    if get_settings().environment == "test":
        from app.integrations.reranker.base import NullReranker

        return NullReranker()

    from app.integrations.reranker.base import CrossEncoderReranker

    return CrossEncoderReranker()
