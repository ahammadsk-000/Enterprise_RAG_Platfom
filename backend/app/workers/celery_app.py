"""Celery application.

Broker + result backend are Redis. Tasks are split across queues per ingestion
stage (`ocr`, `parse`, `chunk`, `embed`, `index`, `graph`, `eval`) so each scales
and fails independently. Task modules are registered via `include` as phases land.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "enterprise_rag",
    broker=str(_settings.redis.dsn),
    backend=str(_settings.redis.dsn),
    include=[
        # "app.workers.tasks.ingestion",
        # "app.workers.tasks.embedding",
        # "app.workers.tasks.graph",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_default_queue="default",
    task_routes={
        "app.workers.tasks.ocr.*": {"queue": "ocr"},
        "app.workers.tasks.ingestion.parse_*": {"queue": "parse"},
        "app.workers.tasks.ingestion.chunk_*": {"queue": "chunk"},
        "app.workers.tasks.embedding.*": {"queue": "embed"},
        "app.workers.tasks.ingestion.index_*": {"queue": "index"},
        "app.workers.tasks.graph.*": {"queue": "graph"},
        "app.workers.tasks.evaluation.*": {"queue": "eval"},
    },
    broker_transport_options={"visibility_timeout": 3600},
    result_expires=86400,
    worker_max_tasks_per_child=200,
)
