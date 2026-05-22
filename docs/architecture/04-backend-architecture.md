# 04 — Backend Architecture

## 1. Layers (Clean Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│ Interface layer        api/v1/routes, api/ws, schemas (DTOs)   │  FastAPI, Pydantic
├─────────────────────────────────────────────────────────────┤
│ Application layer      domains/<ctx>/services                  │  use cases, orchestration
├─────────────────────────────────────────────────────────────┤
│ Domain layer           entities, value objects, policies       │  pure business rules
├─────────────────────────────────────────────────────────────┤
│ Infrastructure layer   repositories/impl, integrations/        │  SQLAlchemy, Qdrant,
│                        db/session, workers/                     │  Neo4j, Ollama, S3, OCR
└─────────────────────────────────────────────────────────────┘
        ▲ dependencies always point upward (inward)
```

## 2. Dependency injection

- FastAPI `Depends` composes the request graph: `get_db` → repositories → services.
- Providers (LLM, vector store, etc.) are resolved from a small **container** that
  reads `Settings` and returns the configured implementation behind a `Protocol`.
- Services receive *interfaces*, never concrete clients — enabling test doubles.

```python
# illustrative
async def get_document_service(
    repo: DocumentRepository = Depends(get_document_repo),
    storage: ObjectStorage = Depends(get_storage),
    bus: TaskBus = Depends(get_task_bus),
) -> DocumentService:
    return DocumentService(repo, storage, bus)
```

## 3. Request flow & middleware order

1. **RequestContext middleware** — assigns `request_id`, starts OTel span, binds
   structlog context.
2. **Auth middleware/dependency** — validates JWT, loads principal.
3. **Tenant scoping** — derives `organization_id`/`workspace_id`, injects into a
   context var consumed by repositories.
4. **Rate limiting** — Redis token bucket per principal/key.
5. Route handler → service → repository.
6. **Exception handlers** — map domain exceptions to RFC 9457 problem responses.

## 4. Persistence

- Async SQLAlchemy 2.0 (`AsyncSession`), declarative `Base` with a naming convention
  for stable constraint names (clean Alembic diffs).
- Repository pattern: an abstract repo per aggregate + a SQLAlchemy implementation.
- Unit-of-work via the request-scoped session; transactions wrap service use cases.
- Alembic for migrations; autogenerate from `db.base.Base.metadata`.

## 5. Background work

- Celery app in `app/workers`, broker + result backend = Redis.
- Tasks are thin: load context → call a domain service → persist → emit next event.
- Queues per stage (`ocr`, `parse`, `chunk`, `embed`, `index`, `graph`, `eval`) so
  each scales and fails independently. Retries with backoff; DLQ for poison messages.

## 6. Configuration

- `core/config.py` — `Settings(BaseSettings)` with nested groups (db, redis, qdrant,
  neo4j, auth, llm, storage, telemetry). Validated at startup; `@lru_cache` accessor.

## 7. Error model

- `core/exceptions.py` defines a hierarchy: `AppError` → `NotFoundError`,
  `ConflictError`, `AuthError`, `PermissionError`, `ValidationError`,
  `ProviderError`, `RateLimitedError`.
- A single set of handlers serializes them to `application/problem+json` with
  `trace_id`, so clients get consistent, machine-readable errors.

## 8. Security touchpoints (backend)

- Password hashing (argon2/bcrypt), JWT signing (RS256 in prod), refresh rotation.
- RBAC enforced in services via a `require_permission` policy helper.
- Tenant guard prevents cross-tenant reads even if an ID is guessed.
- PII detection + masking and prompt-injection screening run in the `security` domain
  and are invoked by ingestion and RAG pipelines.

## 9. Testing strategy

- **unit** — services/policies with fake repositories and provider stubs.
- **integration** — repositories + DB (testcontainers/compose), real Alembic head.
- **e2e** — API via httpx ASGI transport, auth flows, ingestion→retrieval happy path.
- Coverage gate in CI; factory fixtures per aggregate.
