"""Table-aware chunker.

Detects tabular blocks (markdown pipe tables / tab-separated rows) and emits each
as a single TABLE chunk so rows are never split mid-table; surrounding prose is
chunked recursively.
"""

from __future__ import annotations

from app.domains.chunking.chunkers.base import ChunkType, TextChunk
from app.domains.chunking.chunkers.recursive import split_text
from app.domains.chunking.tokenizer import estimate_tokens
from app.domains.ingestion.parsers.base import ParsedDocument


def _is_table_line(line: str) -> bool:
    return line.count("|") >= 2 or line.count("\t") >= 2


class TableAwareChunker:
    name = "table_aware"

    def __init__(self, chunk_size: int = 1000, overlap: int = 150) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, parsed: ParsedDocument) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        ordinal = 0
        for page in parsed.pages:
            for block, is_table in _segment(page.text):
                if is_table:
                    chunks.append(
                        TextChunk(
                            ordinal=ordinal,
                            content=block,
                            chunk_type=ChunkType.TABLE,
                            page_from=page.number,
                            page_to=page.number,
                            token_count=estimate_tokens(block),
                        )
                    )
                    ordinal += 1
                else:
                    for piece in split_text(block, chunk_size=self.chunk_size, overlap=self.overlap):
                        chunks.append(
                            TextChunk(
                                ordinal=ordinal,
                                content=piece,
                                chunk_type=ChunkType.TEXT,
                                page_from=page.number,
                                page_to=page.number,
                                token_count=estimate_tokens(piece),
                            )
                        )
                        ordinal += 1
        return chunks


def _segment(text: str) -> list[tuple[str, bool]]:
    """Group consecutive lines into (block, is_table) segments."""
    segments: list[tuple[str, bool]] = []
    buf: list[str] = []
    buf_is_table: bool | None = None
    for line in text.splitlines():
        is_table = _is_table_line(line)
        if buf_is_table is None or is_table == buf_is_table:
            buf.append(line)
            buf_is_table = is_table
        else:
            segments.append(("\n".join(buf).strip(), bool(buf_is_table)))
            buf, buf_is_table = [line], is_table
    if buf:
        segments.append(("\n".join(buf).strip(), bool(buf_is_table)))
    return [(b, t) for b, t in segments if b]
