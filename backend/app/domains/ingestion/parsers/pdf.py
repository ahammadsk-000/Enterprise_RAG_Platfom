"""PDF parser (PyMuPDF) with OCR fallback for scanned pages.

For each page we extract embedded text; if a page yields little/no text it is
rendered to an image and passed to the OCR engine (scanned-document support).
"""

from __future__ import annotations

from app.core.exceptions import ProviderError
from app.domains.ingestion.parsers.base import ParsedDocument, ParsedPage
from app.integrations.ocr.base import OCREngine

# Below this many characters a page is treated as image-only → OCR fallback.
_MIN_TEXT_CHARS = 16


class PdfParser:
    mimes = frozenset({"application/pdf"})

    async def parse(self, content: bytes, *, filename: str, ocr: OCREngine) -> ParsedDocument:
        try:
            import fitz  # PyMuPDF  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError("PyMuPDF (fitz) is not installed; cannot parse PDFs.") from exc

        pages: list[ParsedPage] = []
        ocr_pages = 0
        with fitz.open(stream=content, filetype="pdf") as doc:
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                ocr_used = False
                if len(text) < _MIN_TEXT_CHARS:
                    pix = page.get_pixmap(dpi=200)
                    text = (await ocr.image_to_text(pix.tobytes("png"))).strip()
                    ocr_used = bool(text)
                    ocr_pages += int(ocr_used)
                pages.append(ParsedPage(number=i, text=text, ocr_used=ocr_used))

        return ParsedDocument.from_pages(pages, ocr_pages=ocr_pages)
