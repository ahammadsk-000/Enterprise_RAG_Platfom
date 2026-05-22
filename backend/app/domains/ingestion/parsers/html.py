"""HTML parser — extracts visible text using the stdlib HTML parser (no deps)."""

from __future__ import annotations

from html.parser import HTMLParser as _StdHTMLParser

from app.domains.ingestion.parsers.base import ParsedDocument, ParsedPage
from app.integrations.ocr.base import OCREngine

_SKIP_TAGS = {"script", "style", "head", "meta", "link"}


class _TextExtractor(_StdHTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data.strip())

    @property
    def text(self) -> str:
        return "\n".join(self._chunks)


class HtmlParser:
    mimes = frozenset({"text/html", "application/xhtml+xml"})

    async def parse(self, content: bytes, *, filename: str, ocr: OCREngine) -> ParsedDocument:
        extractor = _TextExtractor()
        extractor.feed(content.decode("utf-8", errors="replace"))
        return ParsedDocument.from_pages([ParsedPage(number=1, text=extractor.text)])
