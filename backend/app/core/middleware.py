"""Request-context middleware.

Assigns a per-request `request_id`/`trace_id`, binds it into the structlog
context so every log line within the request is correlatable, records latency,
and echoes the id back in the `X-Request-ID` response header.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger
from app.core.metrics import record_request

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.trace_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            elapsed = time.perf_counter() - start
            endpoint = getattr(request.scope.get("route"), "path", request.url.path)
            logger.info("request.completed", duration_ms=round(elapsed * 1000, 2), status=status_code)
            record_request(request.method, endpoint, status_code, elapsed)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
