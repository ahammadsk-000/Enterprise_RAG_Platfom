"""Semantic chunker.

Groups whole sentences up to a soft size budget so chunk boundaries fall on
sentence/paragraph boundaries rather than mid-thought. This is the synchronous,
dependency-free variant; an embedding-similarity merge step can be layered on top
later (it requires the async embedding provider, so it is not done inside the
synchronous chunker contract).
"""

from __future__ import annotations

import re

from app.domains.chunking.chunkers.base import ChunkType, TextChunk
from app.domains.chunking.tokenizer import estimate_tokens
from app.domains.ingestion.parsers.base import ParsedDocument

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _sentences(text: str) -> list[str]:
    out: list[str] = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph:
            out.extend(s.strip() for s in _SENTENCE_RE.split(paragraph) if s.strip())
    return out


class SemanticChunker:
    name = "semantic"

    def __init__(self, target_size: int = 800) -> None:
        self.target_size = target_size

    def chunk(self, parsed: ParsedDocument) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        ordinal = 0
        for page in parsed.pages:
            buf: list[str] = []
            length = 0
            for sentence in _sentences(page.text):
                if buf and length + len(sentence) > self.target_size:
                    chunks.append(self._make(ordinal, " ".join(buf), page.number))
                    ordinal += 1
                    buf, length = [], 0
                buf.append(sentence)
                length += len(sentence) + 1
            if buf:
                chunks.append(self._make(ordinal, " ".join(buf), page.number))
                ordinal += 1
        return chunks

    @staticmethod
    def _make(ordinal: int, content: str, page: int) -> TextChunk:
        return TextChunk(
            ordinal=ordinal,
            content=content,
            chunk_type=ChunkType.TEXT,
            page_from=page,
            page_to=page,
            token_count=estimate_tokens(content),
        )
