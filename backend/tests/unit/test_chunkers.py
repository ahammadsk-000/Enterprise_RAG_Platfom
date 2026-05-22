"""Unit tests for chunking strategies and the registry."""

from __future__ import annotations

from app.domains.chunking.chunkers.base import ChunkType
from app.domains.chunking.chunkers.code_aware import CodeAwareChunker
from app.domains.chunking.chunkers.parent_child import ParentChildChunker
from app.domains.chunking.chunkers.recursive import RecursiveChunker, split_text
from app.domains.chunking.chunkers.registry import get_chunker
from app.domains.chunking.chunkers.table_aware import TableAwareChunker
from app.domains.ingestion.parsers.base import ParsedDocument, ParsedPage


def _doc(text: str) -> ParsedDocument:
    return ParsedDocument.from_pages([ParsedPage(number=1, text=text)])


def test_split_text_respects_size_and_is_nonempty() -> None:
    body = " ".join(f"This is sentence {i} with some filler words." for i in range(200))
    pieces = split_text(body, chunk_size=300, overlap=40)
    assert len(pieces) > 1
    assert all(p.strip() for p in pieces)


def test_recursive_chunker_sequential_ordinals_and_pages() -> None:
    body = "\n\n".join(f"Paragraph {i} " + "word " * 60 for i in range(8))
    chunks = RecursiveChunker(chunk_size=400, overlap=50).chunk(_doc(body))
    assert len(chunks) > 1
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert all(c.page_from == 1 for c in chunks)
    assert all(c.chunk_type == ChunkType.TEXT for c in chunks)


def test_parent_child_produces_parents_and_children() -> None:
    body = " ".join(f"sentence {i} content here." for i in range(300))
    chunks = ParentChildChunker(parent_size=800, child_size=200).chunk(_doc(body))
    parents = [c for c in chunks if not c.embed]
    children = [c for c in chunks if c.embed]
    assert parents and children
    assert all(c.parent_ordinal is not None for c in children)
    assert all(c.metadata.get("role") in {"parent", "child"} for c in chunks)


def test_table_aware_keeps_table_as_single_chunk() -> None:
    text = "Intro paragraph.\n\n| a | b | c |\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |\n\nClosing text."
    chunks = TableAwareChunker().chunk(_doc(text))
    table_chunks = [c for c in chunks if c.chunk_type == ChunkType.TABLE]
    assert len(table_chunks) == 1
    assert "| 1 | 2 | 3 |" in table_chunks[0].content


def test_code_aware_splits_on_definitions() -> None:
    code = "def foo():\n    return 1\n\ndef bar():\n    return 2\n\nclass Baz:\n    pass\n"
    chunks = CodeAwareChunker().chunk(_doc(code))
    assert len(chunks) >= 3
    assert all(c.chunk_type == ChunkType.CODE for c in chunks)


def test_registry_resolves_and_falls_back() -> None:
    assert isinstance(get_chunker("parent_child"), ParentChildChunker)
    assert isinstance(get_chunker(None), RecursiveChunker)
    assert isinstance(get_chunker("does-not-exist"), RecursiveChunker)
