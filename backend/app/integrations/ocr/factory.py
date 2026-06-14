"""OCR engine selection: Tesseract in real environments, no-op under test."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.integrations.ocr.base import NullOCREngine, OCREngine, TesseractOCREngine


@lru_cache(maxsize=1)
def get_ocr_engine() -> OCREngine:
    settings = get_settings()
    if settings.environment == "test" or settings.lite_mode:
        return NullOCREngine()
    return TesseractOCREngine()
