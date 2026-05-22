"""Content hashing, language detection, and derived document metadata."""

from __future__ import annotations

import hashlib

from app.domains.ingestion.parsers.base import ParsedDocument


def content_hash(data: bytes) -> str:
    """SHA-256 hex digest used for duplicate detection."""
    return hashlib.sha256(data).hexdigest()


def detect_language(text: str) -> str | None:
    """Best-effort ISO-639-1 language code (langdetect if available)."""
    sample = text.strip()
    if len(sample) < 20:
        return None
    try:
        from langdetect import DetectorFactory, detect  # noqa: PLC0415

        DetectorFactory.seed = 0
        return detect(sample[:5000])
    except Exception:  # noqa: BLE001 - langdetect missing or undecidable
        return None


def derive_metadata(parsed: ParsedDocument) -> dict:
    """Compute counts and OCR stats stored on the document row."""
    char_count = len(parsed.text)
    word_count = len(parsed.text.split())
    return {
        "char_count": char_count,
        "word_count": word_count,
        "page_count": parsed.page_count,
        "ocr_pages": int(parsed.extra.get("ocr_pages", 0)),
        "empty": char_count == 0,
    }
