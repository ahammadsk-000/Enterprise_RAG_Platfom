# 01 — System Architecture

> Enterprise AI Knowledge Platform — RAG over enterprise documents with multi-tenant
> workspaces, hybrid + graph retrieval, agentic reasoning, citations, and full observability.

## 1. Architectural style

- **Clean Architecture + DDD.** The backend is organized into bounded *domains*
  (`identity`, `workspaces`, `documents`, `ingestion`, `chunking`, `embeddings`,
  `retrieval`, `rag`, `chat`, `agents`, `graphrag`, `evaluation`, `security`,
  `observability`). Each domain owns its models, schemas, repositories, and services.
- **Dependency rule.** Inner layers (domain services, entities) never import outer
  layers (FastAPI, SQLAlchemy concretes). I/O is reached through interfaces
  (`Protocol` / abstract repositories) so providers (LLM, vector store, graph store,
  OCR, object storage) are swappable.
- **Async-first.** All request paths and DB access are `async`. CPU/GPU-heavy work
  (OCR, embedding, parsing) is offloaded to **Celery** workers.
- **Event-driven.** Ingestion is a pipeline of events (`document.uploaded` →
  `document.parsed` → `document.chunked` → `chunks.embedded` → `document.indexed`).
  Events flow through Redis streams / Celery tasks so stages scale independently.
- **CQRS where it pays.** Heavy read models (analytics, retrieval logs) are projected
  into read-optimized tables/materialized views, separate from the write models.
- **Microservice-ready, monolith-first.** Ships as a modular monolith (one FastAPI app
  + worker fleet). Each domain can be extracted into its own service later because the
  boundaries and contracts are already explicit.

## 2. High-level component diagram

```
                         ┌──────────────────────────────────────────────┐
                         │                  Clients                       │
                         │   React SPA  ·  REST/OpenAPI  ·  WebSocket      │
                         └───────────────┬───────────────┬────────────────┘
                                         │ HTTPS / WSS    │
                                  ┌──────▼───────┐        │
                                  │    Nginx     │  (TLS, rate-limit, LB)
                                  └──────┬───────┘
                                         │
                    ┌────────────────────▼─────────────────────┐
                    │            FastAPI API Gateway             │
                    │  AuthN/Z · RBAC · tenant scoping · DI       │
                    │  REST v1 · WS chat · streaming (SSE/WS)     │
                    └───┬─────────┬─────────┬─────────┬──────────┘
                        │         │         │         │
        ┌───────────────▼──┐  ┌───▼─────┐ ┌─▼───────┐ ┌▼──────────────┐
        │  Domain Services │  │  RAG    │ │  Agents │ │  Ingestion API │
        │ identity/ws/docs │  │ engine  │ │LangGraph│ │   (enqueue)    │
        └───────┬──────────┘  └──┬──────┘ └──┬──────┘ └──────┬─────────┘
                │                │           │               │
                │           ┌────▼───────────▼────┐    ┌──────▼─────────┐
                │           │  Retrieval layer     │    │ Celery brokers │
                │           │ dense+BM25+rerank+KG │    │  (Redis)       │
                │           └────┬─────────┬───────┘    └──────┬─────────┘
                │                │         │                   │
   ┌────────────▼───┐   ┌────────▼──┐ ┌────▼─────┐    ┌────────▼─────────┐
   │  PostgreSQL    │   │  Qdrant   │ │  Neo4j   │    │  Worker fleet     │
   │ (system of     │   │ (vectors) │ │ (graph)  │    │ ocr/parse/embed/  │
   │  record, RBAC, │   └───────────┘ └──────────┘    │ index/eval/graph  │
   │  conversations)│                                  └────────┬─────────┘
   └────────┬───────┘   ┌───────────┐  ┌────────────┐           │
            │           │   Redis   │  │ Object store│◄─────────┘
            │           │ cache/queue│  │ (S3/MinIO)  │
            │           └───────────┘  └────────────┘
            │
   ┌────────▼─────────────────────────────────────────────────────────┐
   │  Observability plane: OpenTelemetry → Tempo · Prometheus · Loki ·   │
   │  Grafana · Langfuse/Phoenix (LLM + retrieval + agent tracing)       │
   └────────────────────────────────────────────────────────────────────┘
```

## 3. Request lifecycles

### 3.1 Document ingestion (async pipeline)
1. `POST /api/v1/documents` streams the file to **object storage**; a `Document`
   row is created (`status=UPLOADED`) and a `document.uploaded` task is enqueued.
2. **Parse/OCR worker** extracts text + layout (PyMuPDF/pdfplumber/Tika/Unstructured;
   Tesseract/PaddleOCR fallback for scans). Emits `document.parsed`.
3. **Chunking worker** applies the strategy (semantic / recursive / parent-child /
   table-aware / code-aware). Emits `document.chunked`.
4. **Embedding worker** batch-embeds chunks (Ollama/SentenceTransformers/OpenAI),
   versioned by `embedding_model`. Upserts vectors into **Qdrant**; emits `chunks.embedded`.
5. **Index/graph worker** writes BM25 metadata, extracts entities/relations into
   **Neo4j**, marks `Document.status=INDEXED`.
6. Progress is pushed to the client over WebSocket; every stage is traced.

### 3.2 RAG chat (streaming)
1. Client opens WS `/api/v1/ws/chat/{conversation_id}` (JWT in subprotocol).
2. Query → optional **query expansion** → **hybrid retrieval** (dense + BM25, fused
   with RRF) → optional **graph expansion** → **re-ranker** (cross-encoder) →
   **context compression**.
3. RAG engine builds a grounded, citation-constrained prompt and streams tokens via
   the LLM provider; citations resolve to `page` / `chunk` / `bbox`.
4. Message, retrieved context, citations, token usage, and a faithfulness score are
   persisted; the full trace lands in Langfuse + OTel.

## 4. Cross-cutting concerns

| Concern        | Mechanism |
|----------------|-----------|
| AuthN          | JWT (access+refresh), OAuth2 password + Google/Microsoft SSO (OIDC) |
| AuthZ          | RBAC (org/workspace roles) + policy checks in service layer |
| Multi-tenancy  | Every row carries `organization_id`; queries are tenant-scoped by a session-bound dependency; vector/graph payloads filtered by tenant + workspace |
| Config         | Pydantic-Settings, 12-factor env, per-environment profiles |
| Errors         | Typed domain exceptions → RFC 9457 problem+json responses |
| Logging        | structlog JSON, request/trace IDs, PII redaction |
| Rate limiting  | Redis token bucket per tenant/key at gateway |
| Idempotency    | Upload + task dedupe via content hash; idempotency keys on mutating APIs |
| Caching        | Redis: embeddings, retrieval results, sessions, rate-limit counters |

## 5. Quality attributes & how they're met

- **Scalability** — stateless API replicas; independently scaled worker queues;
  Qdrant sharding; read-model projections; connection pooling + pgbouncer.
- **Extensibility** — provider interfaces for LLM/embeddings/vector/graph/OCR/storage;
  pluggable chunkers and retrievers via a registry.
- **Security** — tenant isolation, encryption in transit/at rest, audit log, PII
  detection + masking, prompt-injection defenses (see `docs/architecture/` security).
- **Observability** — OTel spans across API→retrieval→LLM→agents; Prometheus metrics;
  Loki logs; Langfuse/Phoenix for LLM-level tracing and eval.
- **Maintainability** — strict typing (mypy), Pydantic v2 contracts, small modules,
  high test coverage with unit/integration/e2e tiers.
