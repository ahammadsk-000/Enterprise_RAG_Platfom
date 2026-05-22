"""Task bus abstraction — decouples services from Celery.

`CeleryTaskBus` enqueues the real pipeline task; `NullTaskBus` records calls for
tests. Services depend on the `TaskBus` Protocol, never on Celery directly.
"""

from __future__ import annotations

import uuid
from typing import Protocol


class TaskBus(Protocol):
    def enqueue_ingestion(self, document_id: uuid.UUID) -> None: ...


class CeleryTaskBus:
    def enqueue_ingestion(self, document_id: uuid.UUID) -> None:
        from app.workers.tasks.ingestion import ingest_document

        ingest_document.delay(str(document_id))


class NullTaskBus:
    """No-op bus that records enqueued ids (tests / synchronous dev)."""

    def __init__(self) -> None:
        self.enqueued: list[uuid.UUID] = []

    def enqueue_ingestion(self, document_id: uuid.UUID) -> None:
        self.enqueued.append(document_id)
