"""Recursive character chunker (default strategy).

Splits text along a separator hierarchy (paragraph → line → sentence → word →
char), packing pieces up to `chunk_size` characters and prepending a small overlap
from the previous chunk to preserve context across boundaries. Chunks carry the
page number they came from.
"""

from __future__ import annotations

from app.domains.chunking.chunkers.base import ChunkType, TextChunk
from app.domains.chunking.tokenizer import estimate_tokens
from app.domains.ingestion.parsers.base import ParsedDocument

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def split_text(text: str, *, chunk_size: int, overlap: int, separators: list[str] | None = None) -> list[str]:
    """Recursively split `text` into chunks of at most ~`chunk_size` chars."""
    seps = separators if separators is not None else _SEPARATORS
    raw = _recursive_split(text, chunk_size, seps)
    return _apply_overlap([c for c in (s.strip() for s in raw) if c], overlap)


def _recursive_split(text: str, size: int, seps: list[str]) -> list[str]:
    if len(text) <= size or not text:
        return [text] if text else []
    sep = next((s for s in seps if s and s in text), "")
    parts = text.split(sep) if sep else list(text)
    rest = seps[seps.index(sep) + 1 :] if sep in seps else [""]

    chunks: list[str] = []
    current = ""
    for part in parts:
        piece = part + sep if sep else part
        if len(piece) > size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_recursive_split(piece, size, rest or [""]))
        elif len(current) + len(piece) <= size:
            current += piece
        else:
            if current:
                chunks.append(current)
            current = piece
    if current:
        chunks.append(current)
    return chunks


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    out: list[str] = [chunks[0]]
    for prev, cur in zip(chunks, chunks[1:], strict=False):
        tail = prev[-overlap:].lstrip()
        out.append(f"{tail} {cur}".strip())
    return out


class RecursiveChunker:
    name = "recursive"

    def __init__(self, chunk_size: int = 1000, overlap: int = 150) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, parsed: ParsedDocument) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        ordinal = 0
        for page in parsed.pages:
            for piece in split_text(page.text, chunk_size=self.chunk_size, overlap=self.overlap):
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
