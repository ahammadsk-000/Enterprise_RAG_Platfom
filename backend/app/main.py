"""FastAPI application factory + lifespan.

Wires configuration, logging, middleware, exception handlers, CORS, and the v1
router. Heavy clients (vector store, graph store, LLM) are initialized lazily via
the provider container in later phases; here we manage the DB engine lifecycle.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.metrics import render_metrics
from app.core.middleware import RequestContextMiddleware
from app.core.ratelimit import InMemoryRateLimiter, RateLimitMiddleware, SecurityHeadersMiddleware
from app.core.telemetry import setup_telemetry
from app.db.session import dispose_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown lifecycle."""
    settings = get_settings()
    logger.info("app.startup", environment=settings.environment, version=app.version)
    yield
    await dispose_engine()
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware, limiter=InMemoryRateLimiter(limit=settings.rate_limit_per_minute)
    )
    # Required by Authlib to carry OAuth state/nonce across the SSO redirect.
    app.add_middleware(SessionMiddleware, secret_key=settings.auth.secret_key, https_only=settings.is_production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        body, content_type = render_metrics()
        return Response(content=body, media_type=content_type)

    setup_telemetry(app)
    return app


app = create_app()
