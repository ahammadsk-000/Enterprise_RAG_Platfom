"""Domain exception hierarchy and RFC 9457 (problem+json) handlers.

Domain/service code raises typed `AppError` subclasses; the API layer maps them to
consistent `application/problem+json` responses carrying a `trace_id`. This keeps
HTTP concerns out of the domain while giving clients machine-readable errors.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base application error. Subclasses set `status_code` and `error_type`."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type: str = "internal_error"

    def __init__(self, detail: str, *, extra: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra or {}


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_type = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_type = "conflict"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_type = "validation_error"


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_type = "authentication_error"


class PermissionError(AppError):  # noqa: A001 - deliberate domain name
    status_code = status.HTTP_403_FORBIDDEN
    error_type = "permission_denied"


class RateLimitedError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_type = "rate_limited"


class ProviderError(AppError):
    """An external provider (LLM, vector store, OCR, etc.) failed."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_type = "provider_error"


def _problem(request: Request, status_code: int, error_type: str, detail: str, **extra: Any) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)
    body: dict[str, Any] = {
        "type": f"https://errors.enterprise-rag/{error_type}",
        "title": error_type.replace("_", " ").title(),
        "status": status_code,
        "detail": detail,
        "instance": str(request.url),
        "trace_id": trace_id,
    }
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body, media_type="application/problem+json")


def register_exception_handlers(app: FastAPI) -> None:
    """Wire the exception handlers onto the FastAPI app."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("app_error", error_type=exc.error_type, detail=exc.detail, **exc.extra)
        return _problem(request, exc.status_code, exc.error_type, exc.detail, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed.",
            errors=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error=str(exc))
        return _problem(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
        )
