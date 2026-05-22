"""Document lifecycle + ingestion pipeline enums."""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Document lifecycle. Phase 2 drives UPLOADED → PARSING → PARSED (or FAILED);
    CHUNKING…INDEXED are reached in Phases 3–4."""

    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"


class IngestionStage(StrEnum):
    PARSE = "parse"
    OCR = "ocr"
    METADATA = "metadata"
    CHUNK = "chunk"
    EMBED = "embed"
    INDEX = "index"
    GRAPH = "graph"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
