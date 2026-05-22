"""Chunker contracts.

`TextChunk` is the transient output of a chunker (the persisted form is the `Chunk`
ORM model). Chunkers are synchronous and dependency-light; they consume a
`ParsedDocument` and emit ordered chunks with page provenance and an `embed` flag
(parent chunks in parent/child strategies are persisted but not embedded).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from app.domains.ingestion.parsers.base import ParsedDocument


class ChunkType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    CODE = "code"
    CAPTION = "caption"


@dataclass(slots=True)
class TextChunk:
    ordinal: int
    content: str
    chunk_type: ChunkType = ChunkType.TEXT
    page_from: int | None = None
    page_to: int | None = None
    token_count: int = 0
    parent_ordinal: int | None = None
    embed: bool = True
    metadata: dict = field(default_factory=dict)


class Chunker(Protocol):
    name: str

    def chunk(self, parsed: ParsedDocument) -> list[TextChunk]: ...
