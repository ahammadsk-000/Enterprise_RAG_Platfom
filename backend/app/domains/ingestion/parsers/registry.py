"""Parser registry — resolves a `DocumentParser` by MIME type.

New formats are added by registering a parser; nothing else changes.
"""

from __future__ import annotations

import mimetypes

from app.core.exceptions import ValidationError
from app.domains.ingestion.parsers.base import DocumentParser
from app.domains.ingestion.parsers.docx import DocxParser
from app.domains.ingestion.parsers.html import HtmlParser
from app.domains.ingestion.parsers.image import ImageParser
from app.domains.ingestion.parsers.pdf import PdfParser
from app.domains.ingestion.parsers.plain_text import PlainTextParser

_PARSERS: list[DocumentParser] = [
    PlainTextParser(),
    HtmlParser(),
    PdfParser(),
    DocxParser(),
    ImageParser(),
]

_BY_MIME: dict[str, DocumentParser] = {mime: p for p in _PARSERS for mime in p.mimes}


def supported_mimes() -> frozenset[str]:
    return frozenset(_BY_MIME)


def get_parser(mime_type: str) -> DocumentParser:
    parser = _BY_MIME.get(mime_type)
    if parser is None:
        raise ValidationError(
            f"Unsupported document type: {mime_type}",
            extra={"supported": sorted(_BY_MIME)},
        )
    return parser


def guess_mime(filename: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or fallback
