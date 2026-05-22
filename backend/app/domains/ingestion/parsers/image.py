"""Image parser — runs OCR over the image bytes."""

from __future__ import annotations

from app.domains.ingestion.parsers.base import ParsedDocument, ParsedPage
from app.integrations.ocr.base import OCREngine


class ImageParser:
    mimes = frozenset({"image/png", "image/jpeg", "image/tiff", "image/bmp", "image/webp"})

    async def parse(self, content: bytes, *, filename: str, ocr: OCREngine) -> ParsedDocument:
        text = (await ocr.image_to_text(content)).strip()
        return ParsedDocument.from_pages([ParsedPage(number=1, text=text, ocr_used=bool(text))], ocr_pages=1)
