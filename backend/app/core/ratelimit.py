"""Rate limiting + security-header middleware (hardening).

`InMemoryRateLimiter` is a fixed-window counter keyed by client (used by default and
in tests). In production a Redis-backed limiter (shared across replicas) is wired in
behind the same `allow()` contract. Health/metrics/doc paths are exempt.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_EXEMPT_PREFIXES = ("/healthz", "/readyz", "/metrics", "/docs", "/redoc", "/openapi")


class InMemoryRateLimiter:
    def __init__(self, limit: int, window_s: int = 60) -> None:
        self.limit = limit
        self.window_s = window_s
        self._buckets: dict[str, tuple[int, float]] = {}

    def allow(self, key: str) -> bool:
        if self.limit <= 0:
            return True
        now = time.monotonic()
        count, window_start = self._buckets.get(key, (0, now))
        if now - window_start >= self.window_s:
            count, window_start = 0, now
        count += 1
        self._buckets[key] = (count, window_start)
        return count <= self.limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: InMemoryRateLimiter) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._limiter = limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        client = request.client.host if request.client else "anonymous"
        if not self._limiter.allow(f"{client}:{path.split('/')[3] if path.count('/') > 3 else path}"):
            return JSONResponse(
                status_code=429,
                media_type="application/problem+json",
                content={
                    "type": "https://errors.enterprise-rag/rate_limited",
                    "title": "Rate Limited",
                    "status": 429,
                    "detail": "Too many requests; slow down.",
                },
                headers={"Retry-After": str(self._limiter.window_s)},
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-XSS-Protection", "0")
        return response
