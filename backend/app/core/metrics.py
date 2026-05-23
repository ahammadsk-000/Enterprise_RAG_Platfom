"""Prometheus metrics.

`prometheus_client` is optional: when absent, recording is a no-op and `/metrics`
returns a short notice, so the app runs without the dependency. The middleware
records request count + latency labelled by method, route template, and status.
"""

from __future__ import annotations

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    _ENABLED = True
except ImportError:  # pragma: no cover - optional dependency
    _ENABLED = False
    CONTENT_TYPE_LATEST = "text/plain"

if _ENABLED:
    REQUEST_COUNT = Counter(
        "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
    )


def record_request(method: str, endpoint: str, status: int, duration_s: float) -> None:
    if not _ENABLED:
        return
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration_s)


def render_metrics() -> tuple[bytes, str]:
    if not _ENABLED:
        return b"# prometheus_client not installed\n", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST
