"""Chunking strategy registry.

Maps a strategy name (configurable per workspace) to a chunker factory. Defaults to
`recursive`. Unknown strategies fall back to the default with a logged warning.
"""

from __future__ import annotations

from collections.abc import Callable

from app.core.logging import get_logger
from app.domains.chunking.chunkers.base import Chunker
from app.domains.chunking.chunkers.code_aware import CodeAwareChunker
from app.domains.chunking.chunkers.parent_child import ParentChildChunker
from app.domains.chunking.chunkers.recursive import RecursiveChunker
from app.domains.chunking.chunkers.semantic import SemanticChunker
from app.domains.chunking.chunkers.table_aware import TableAwareChunker

logger = get_logger(__name__)

DEFAULT_STRATEGY = "recursive"

_FACTORIES: dict[str, Callable[[], Chunker]] = {
    "recursive": RecursiveChunker,
    "parent_child": ParentChildChunker,
    "semantic": SemanticChunker,
    "table_aware": TableAwareChunker,
    "code_aware": CodeAwareChunker,
}


def available_strategies() -> list[str]:
    return sorted(_FACTORIES)


def get_chunker(strategy: str | None = None) -> Chunker:
    name = strategy or DEFAULT_STRATEGY
    factory = _FACTORIES.get(name)
    if factory is None:
        logger.warning("chunking.unknown_strategy", strategy=name, fallback=DEFAULT_STRATEGY)
        factory = _FACTORIES[DEFAULT_STRATEGY]
    return factory()
