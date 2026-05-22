"""Unit tests for hashing + derived metadata."""

from __future__ import annotations

from app.domains.ingestion.parsers.base import ParsedDocument, ParsedPage
from app.domains.ingestion.services.metadata import content_hash, derive_metadata, detect_language


def test_content_hash_is_deterministic_sha256() -> None:
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")
    assert len(content_hash(b"abc")) == 64


def test_derive_metadata_counts() -> None:
    parsed = ParsedDocument.from_pages(
        [ParsedPage(1, "one two three", ocr_used=True), ParsedPage(2, "four")],
        ocr_pages=1,
    )
    meta = derive_metadata(parsed)
    assert meta["word_count"] == 4
    assert meta["page_count"] == 2
    assert meta["ocr_pages"] == 1
    assert meta["empty"] is False


def test_detect_language_returns_none_for_short_text() -> None:
    assert detect_language("hi") is None
