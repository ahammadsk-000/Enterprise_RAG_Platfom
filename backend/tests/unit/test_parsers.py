"""Unit tests for document parsers and the parser registry (dependency-free paths)."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.domains.ingestion.parsers.html import HtmlParser
from app.domains.ingestion.parsers.plain_text import PlainTextParser
from app.domains.ingestion.parsers.registry import get_parser, guess_mime, supported_mimes
from app.integrations.ocr.base import NullOCREngine

_OCR = NullOCREngine()


@pytest.mark.asyncio
async def test_plain_text_parser() -> None:
    parsed = await PlainTextParser().parse(b"hello world\nsecond line", filename="a.txt", ocr=_OCR)
    assert parsed.page_count == 1
    assert "hello world" in parsed.text
    assert parsed.pages[0].number == 1


@pytest.mark.asyncio
async def test_html_parser_strips_tags_and_scripts() -> None:
    html = b"<html><head><style>x{}</style></head><body><h1>Title</h1><script>bad()</script><p>Body text</p></body></html>"
    parsed = await HtmlParser().parse(html, filename="a.html", ocr=_OCR)
    assert "Title" in parsed.text
    assert "Body text" in parsed.text
    assert "bad()" not in parsed.text
    assert "x{}" not in parsed.text


def test_registry_resolves_known_mime() -> None:
    assert isinstance(get_parser("text/plain"), PlainTextParser)
    assert "application/pdf" in supported_mimes()


def test_registry_rejects_unknown_mime() -> None:
    with pytest.raises(ValidationError):
        get_parser("application/x-totally-unknown")


def test_guess_mime_from_filename() -> None:
    assert guess_mime("report.pdf") == "application/pdf"
    assert guess_mime("notes.md") in {"text/markdown", "text/x-markdown"}
    assert guess_mime("noextension") == "application/octet-stream"
