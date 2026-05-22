# syntax=docker/dockerfile:1.7
# Multi-stage build shared by the API and the Celery workers (differ by entrypoint).

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
# OS deps for document processing (PyMuPDF, OCR) — extend as Phase 2 lands.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libmagic1 poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY backend/pyproject.toml ./
RUN pip install --upgrade pip && pip install ".[dev]"

FROM base AS runtime
# Non-root user
RUN useradd --create-home --uid 1000 appuser
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY backend/ /app/
USER appuser
EXPOSE 8000

# API entrypoint (overridden by the worker service in compose/helm).
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "120"]
