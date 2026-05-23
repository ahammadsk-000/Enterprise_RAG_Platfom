"""Task bus abstraction — decouples services from Celery.

`CeleryTaskBus` enqueues the real pipeline task; `NullTaskBus` records calls for
tests. Services depend on the `TaskBus` Protocol, never on Celery directly.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskBus(Protocol):
    def enqueue_ingestion(self, document_id: uuid.UUID) -> None: ...


class CeleryTaskBus:
    def enqueue_ingestion(self, document_id: uuid.UUID) -> None:
        from app.workers.tasks.ingestion import ingest_document

        ingest_document.delay(str(document_id))


# Keep strong references so fire-and-forget tasks aren't garbage-collected mid-run.
_inline_tasks: set[asyncio.Task] = set()


class InlineTaskBus:
    """Runs the ingestion pipeline in-process (demo/dev — no Celery broker/worker).

    Schedules the async pipeline on the running event loop when called from a request
    handler; falls back to a blocking run if there is no loop. Relies on the in-memory
    providers (ENVIRONMENT=test) being process-wide singletons so the API and the
    pipeline share the same vector/graph/object stores.
    """

    def enqueue_ingestion(self, document_id: uuid.UUID) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._safe_run(document_id))
            return
        task = loop.create_task(self._safe_run(document_id))
        _inline_tasks.add(task)
        task.add_done_callback(_inline_tasks.discard)

    @staticmethod
    async def _safe_run(document_id: uuid.UUID) -> None:
        from app.workers.tasks.ingestion import run_ingestion_pipeline

        try:
            await run_ingestion_pipeline(document_id)
        except Exception as exc:  # noqa: BLE001 - background task: log, never crash the loop
            logger.warning("ingestion.inline.failed", document_id=str(document_id), error=str(exc))


class NullTaskBus:
    """No-op bus that records enqueued ids (tests / synchronous dev)."""

    def __init__(self) -> None:
        self.enqueued: list[uuid.UUID] = []

    def enqueue_ingestion(self, document_id: uuid.UUID) -> None:
        self.enqueued.append(document_id)
