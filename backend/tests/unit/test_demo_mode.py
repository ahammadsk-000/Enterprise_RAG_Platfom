"""Verify the INGESTION_INLINE toggle selects the in-process task bus (demo mode)."""

from __future__ import annotations

import pytest

from app.core.config import get_settings


@pytest.fixture
def _clean_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_inline_toggle_selects_inline_bus(monkeypatch, _clean_settings) -> None:
    from app.api.deps import get_task_bus
    from app.domains.ingestion.task_bus import InlineTaskBus

    monkeypatch.setenv("INGESTION_INLINE", "true")
    get_settings.cache_clear()
    assert isinstance(get_task_bus(), InlineTaskBus)


def test_default_selects_celery_bus(monkeypatch, _clean_settings) -> None:
    from app.api.deps import get_task_bus
    from app.domains.ingestion.task_bus import CeleryTaskBus

    monkeypatch.delenv("INGESTION_INLINE", raising=False)
    get_settings.cache_clear()
    assert isinstance(get_task_bus(), CeleryTaskBus)
