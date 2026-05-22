"""Plain-text family parser (txt, markdown, csv) — dependency-free."""

from __future__ import annotations

from app.domains.ingestion.parsers.base import ParsedDocument, ParsedPage
from app.integrations.ocr.base import OCREngine


class PlainTextParser:
    mimes = frozenset({"text/plain", "text/markdown", "text/csv", "application/csv"})

    async def parse(self, content: bytes, *, filename: str, ocr: OCREngine) -> ParsedDocument:
        text = content.decode("utf-8", errors="replace").strip()
        return ParsedDocument.from_pages([ParsedPage(number=1, text=text)])
