"""OpenTelemetry tracing setup.

Instruments the FastAPI app and exports spans via OTLP when telemetry is enabled and
the OTel packages are installed. Entirely best-effort: any import/exporter problem is
logged and skipped so it can never break application startup.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_telemetry(app: Any) -> None:
    settings = get_settings()
    if not settings.telemetry.enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:  # pragma: no cover - optional dependency
        logger.info("otel.not_installed")
        return

    try:
        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.telemetry.service_name})
        )
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.telemetry.exporter_otlp_endpoint, insecure=True)
            )
        )
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("otel.instrumented", endpoint=settings.telemetry.exporter_otlp_endpoint)
    except Exception as exc:  # noqa: BLE001 - never fail startup on telemetry
        logger.warning("otel.setup_failed", error=str(exc))
