"""OCR engine interface + Tesseract implementation.

Used as a fallback when a PDF page yields little/no embedded text (scanned docs),
and as the primary path for image documents. PaddleOCR can be added as an
alternative implementation behind the same `OCREngine` Protocol.
"""

from __future__ import annotations

from typing import Protocol

from app.core.exceptions import ProviderError


class OCREngine(Protocol):
    async def image_to_text(self, image_bytes: bytes, lang: str = "eng") -> str: ...


class TesseractOCREngine:
    """pytesseract-backed OCR (lazy import; requires the tesseract binary)."""

    async def image_to_text(self, image_bytes: bytes, lang: str = "eng") -> str:
        import asyncio

        return await asyncio.to_thread(self._run, image_bytes, lang)

    @staticmethod
    def _run(image_bytes: bytes, lang: str) -> str:
        try:
            import io  # noqa: PLC0415

            import pytesseract  # noqa: PLC0415
            from PIL import Image  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError("pytesseract/Pillow not installed; OCR unavailable.") from exc

        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image, lang=lang)


class NullOCREngine:
    """No-op OCR engine (tests / environments without tesseract)."""

    async def image_to_text(self, image_bytes: bytes, lang: str = "eng") -> str:
        return ""
