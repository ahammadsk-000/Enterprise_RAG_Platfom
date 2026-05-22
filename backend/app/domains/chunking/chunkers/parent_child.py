"""Parent/child chunker.

Produces large *parent* chunks (broad context) and small *child* chunks (precise
recall). Children are embedded and retrieved; the parent supplies surrounding
context at answer time. Parents are persisted with `embed=False`.
"""

from __future__ import annotations

from app.domains.chunking.chunkers.base import ChunkType, TextChunk
from app.domains.chunking.chunkers.recursive import split_text
from app.domains.chunking.tokenizer import estimate_tokens
from app.domains.ingestion.parsers.base import ParsedDocument


class ParentChildChunker:
    name = "parent_child"

    def __init__(self, parent_size: int = 2000, child_size: int = 400, child_overlap: int = 80) -> None:
        self.parent_size = parent_size
        self.child_size = child_size
        self.child_overlap = child_overlap

    def chunk(self, parsed: ParsedDocument) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        ordinal = 0
        for page in parsed.pages:
            for parent_text in split_text(page.text, chunk_size=self.parent_size, overlap=0):
                parent_ordinal = ordinal
                chunks.append(
                    TextChunk(
                        ordinal=parent_ordinal,
                        content=parent_text,
                        chunk_type=ChunkType.TEXT,
                        page_from=page.number,
                        page_to=page.number,
                        token_count=estimate_tokens(parent_text),
                        embed=False,
                        metadata={"role": "parent"},
                    )
                )
                ordinal += 1
                for child_text in split_text(
                    parent_text, chunk_size=self.child_size, overlap=self.child_overlap
                ):
                    chunks.append(
                        TextChunk(
                            ordinal=ordinal,
                            content=child_text,
                            chunk_type=ChunkType.TEXT,
                            page_from=page.number,
                            page_to=page.number,
                            token_count=estimate_tokens(child_text),
                            parent_ordinal=parent_ordinal,
                            embed=True,
                            metadata={"role": "child"},
                        )
                    )
                    ordinal += 1
        return chunks
