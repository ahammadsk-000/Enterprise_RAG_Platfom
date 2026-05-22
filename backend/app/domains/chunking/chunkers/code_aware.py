"""Code-aware chunker.

Splits source text on top-level definition boundaries (def/class/function/etc.) so
a function or class stays intact within a chunk. Oversized definitions fall back to
recursive splitting.
"""

from __future__ import annotations

import re

from app.domains.chunking.chunkers.base import ChunkType, TextChunk
from app.domains.chunking.chunkers.recursive import split_text
from app.domains.chunking.tokenizer import estimate_tokens
from app.domains.ingestion.parsers.base import ParsedDocument

_DEF_RE = re.compile(r"^(?:\s*)(def |class |func |function |public |private |export )", re.MULTILINE)


class CodeAwareChunker:
    name = "code_aware"

    def __init__(self, chunk_size: int = 1500, overlap: int = 0) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, parsed: ParsedDocument) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        ordinal = 0
        for page in parsed.pages:
            for block in self._split_on_defs(page.text):
                pieces = (
                    [block]
                    if len(block) <= self.chunk_size
                    else split_text(block, chunk_size=self.chunk_size, overlap=self.overlap)
                )
                for piece in pieces:
                    chunks.append(
                        TextChunk(
                            ordinal=ordinal,
                            content=piece,
                            chunk_type=ChunkType.CODE,
                            page_from=page.number,
                            page_to=page.number,
                            token_count=estimate_tokens(piece),
                        )
                    )
                    ordinal += 1
        return chunks

    def _split_on_defs(self, text: str) -> list[str]:
        starts = [m.start() for m in _DEF_RE.finditer(text)]
        if not starts:
            return [text] if text.strip() else []
        if starts[0] != 0:
            starts.insert(0, 0)
        bounds = [*starts, len(text)]
        blocks = [text[bounds[i] : bounds[i + 1]].strip() for i in range(len(starts))]
        return [b for b in blocks if b]
