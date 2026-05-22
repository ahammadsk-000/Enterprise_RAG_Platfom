"""Parser contracts: `ParsedDocument`/`ParsedPage` and the `DocumentParser` Protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.integrations.ocr.base import OCREngine


@dataclass(slots=True)
class ParsedPage:
    number: int
    text: str
    ocr_used: bool = False


@dataclass(slots=True)
class ParsedDocument:
    text: str
    pages: list[ParsedPage]
    page_count: int
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_pages(cls, pages: list[ParsedPage], **extra: object) -> ParsedDocument:
        text = "\n\n".join(p.text for p in pages if p.text)
        return cls(text=text, pages=pages, page_count=len(pages), extra=dict(extra))


class DocumentParser(Protocol):
    mimes: frozenset[str]

    async def parse(self, content: bytes, *, filename: str, ocr: OCREngine) -> ParsedDocument: ...
