# Enterprise RAG Platform — Project Details

A single document a newcomer can read to understand **what this project is, what it
does, every piece of technology in it, how the pieces fit together, and how to run
it**. No code reading required.

---

## 1. What is this project?

A **production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform**
for enterprise knowledge. Drop in your documents (PDFs, Word, text, images, HTML,
code), and the system gives you:

- **Citation-grounded streaming chat** over your documents — every claim points back
  to the chunk it came from.
- **Hybrid search** that combines keyword (BM25), dense vectors, and reranking.
- **Knowledge graph** built from your documents for entity/relation exploration.
- **Multi-agent research** workflows that decompose questions, retrieve, verify, and
  synthesize.
- **Workspaces** so teams can keep document sets separate.
- **Evaluation harness** to score answer quality and detect hallucinations.
- **Full observability** — metrics, traces, structured logs, LLM-call tracing.

It is **multi-tenant by design** (org → users → workspaces → documents), with
RBAC, JWT auth, optional OIDC SSO (Google / Microsoft), and tenant isolation at the
storage, vector, and graph layers.

---

## 2. Live deployment

The project is wired to deploy for **$0/month** on free tiers:

| Layer | Host | URL pattern |
|---|---|---|
| Frontend (Vite + React) | **Vercel** (free, always on) | `https://<your-app>.vercel.app` |
| Backend (FastAPI) | **Render** Web Service (free, sleeps after 15 min idle) | `https://enterprise-rag-backend-<id>.onrender.com` |
| Database (Postgres) | **Neon** (free serverless Postgres) | `…neon.tech/neondb` |
| LLM (chat answers) | **Groq** (free OpenAI-compatible API, `llama-3.3-70b-versatile`) | `api.groq.com/openai/v1` |

A `render.yaml` blueprint and `frontend/vercel.json` are included. The full
walkthrough is in [`docs/DEPLOY_FREE.md`](docs/DEPLOY_FREE.md).

A live end-to-end probe (`scripts/e2e_probe.py`) exercises every layer
(register → upload → ingestion → search → RAG → chat → graph → agents → cleanup)
and is the canonical "is everything working?" check.

---

## 3. Feature catalogue

### 3.1 Identity & access
- Email/password registration, login, JWT access + refresh tokens.
- **OIDC SSO** via Authlib — Google and Microsoft Entra/Azure AD out of the box.
- **RBAC** with roles (`owner`, `admin`, `member`, `viewer`) and explicit
  permission strings checked at every protected endpoint.
- **Multi-tenancy**: every row carries `organization_id`; queries are scoped at
  the repository layer so cross-tenant leakage is impossible.
- **Rate limiting** — in-memory fixed-window limiter middleware (configurable per
  client per minute; Redis-backed variant available for multi-replica deployments).

### 3.2 Document ingestion
- **Upload** any of: PDF, DOCX, plain text, Markdown, HTML, images.
- Duplicate detection by **SHA-256 content hash** (re-uploading a file returns
  the existing row; re-uploading a *failed* file automatically retries).
- **OCR fallback** for scanned/image PDFs (Tesseract in production, no-op in
  free-tier `LITE_MODE`).
- Background pipeline runs through **5 stages**, each tracked as an
  `IngestionJob` row so status is queryable per stage:
  1. **PARSE** — extract text per page (PyMuPDF for PDFs, python-docx for Word,
     BeautifulSoup-ish for HTML, native readers for txt/md, OCR for images).
  2. **METADATA** — language detection (langdetect), char/word/page counts,
     persist extracted text artifact to object storage.
  3. **CHUNK** — split into structured chunks (see chunking strategies below).
  4. **INDEX** — embed each chunk + upsert into the tenant's vector collection;
     BM25 index is also kept in Postgres FTS.
  5. **GRAPH** — extract entities/relations and upsert into the knowledge
     graph. **Best-effort**: a graph failure (e.g. LLM rate limit) does *not*
     fail the document — it stays `INDEXED` and chat-able; the soft error is
     recorded in metadata.

The pipeline runs **inline** (in-process, no Celery) when `INGESTION_INLINE=true`
(free-tier), or **via Celery** with a Redis broker in production.

### 3.3 Chunking strategies
Configurable per workspace. Five built-in strategies:

| Strategy | Behaviour |
|---|---|
| `recursive` (default) | Recursive character split — paragraphs → sentences → words. Best general-purpose default. |
| `semantic` | Sentence-aware split that respects paragraph boundaries and a soft token budget. |
| `parent_child` | Stores fine-grained children for retrieval and coarse parents for context — the "small chunks for matching, big chunks for answering" pattern. |
| `table_aware` | Detects table-like layouts and keeps them as one chunk so structure isn't shredded. |
| `code_aware` | Splits along function/class boundaries; keeps imports near their usage. |

Unknown strategy names fall back to `recursive` with a logged warning.

### 3.4 Embeddings
Provider abstraction (Protocol). Three real implementations + a deterministic
fake:

| Provider | When to use |
|---|---|
| **Ollama** | Local LLM/embedding server (`nomic-embed-text` by default). |
| **SentenceTransformers** | In-process, GPU-friendly. Pulls ~600 MB of torch. |
| **OpenAI-compatible** | OpenAI, Voyage AI, Mistral La Plateforme, Jina AI, vLLM. Handles base URLs with or without trailing `/v1`. |
| **Fake** (deterministic) | Hash-based unit vectors. Used in tests and `LITE_MODE` — gives reproducible similarity but no semantics; BM25 + Postgres FTS carries retrieval quality. |

An **embedding cache** keyed by `(version_id, content_hash)` skips recomputation
across re-indexes.

### 3.5 Vector store
- **Qdrant** in production (one collection per organization, configurable prefix).
- **In-memory** under tests / `LITE_MODE` — exact same API surface so the rest of
  the pipeline doesn't notice.
- Tenant isolation is enforced both at the collection level *and* through payload
  filters (org_id, workspace_id, document_id).

### 3.6 Retrieval & RAG
- **BM25** retriever via Postgres FTS (`tsvector` + GIN index).
- **Dense** retriever via vector store top-k.
- **Hybrid** retriever — **Reciprocal Rank Fusion (RRF)** over BM25 and dense.
- Optional **cross-encoder reranker** on top of the fused list (null in LITE_MODE).
- **Workspace scoping** — every retrieval call filters by workspace if provided.
- **Citations** — every answer returns the chunks it referenced, with score,
  page number, and document id.
- **Streaming** answers via Server-Sent Events / WebSocket so tokens appear as
  the LLM produces them.

### 3.7 Knowledge graph (Graph RAG)
- **Entity extractor** — LLM-based (structured JSON output) or rule-based regex.
  LITE_MODE uses rule-based to save quota.
- **Graph store** — Neo4j in production, in-memory in LITE_MODE.
- **Graph-augmented retrieval** — k-hop neighbour expansion can widen a query
  before hybrid retrieval.
- **Explore endpoint** lets users walk the graph from seed entities.

### 3.8 Chat
- **Conversations** persist in Postgres with title, last-message timestamp.
- **Memory** — recent messages are summarized and injected as context.
- **WebSocket** chat endpoint streams the answer + citations.
- The frontend reconstructs `ws://` vs `wss://` from the API base URL so it
  works both locally and on the Vercel HTTPS deploy.

### 3.9 Multi-agent research
Built on LangGraph-style supervisor pattern:

- **Decomposer** breaks the question into sub-queries.
- **Researcher** runs retrieval for each sub-query.
- **Verifier** checks claims against retrieved evidence.
- **Synthesizer** writes the final cited answer.

Exposed at `POST /api/v1/agents/research`.

### 3.10 Evaluation
- **Datasets** — store labelled samples (question, expected answer, citations).
- **Runner** computes retrieval metrics (recall@k, MRR), generation metrics
  (faithfulness, answer relevance), and a hallucination signal.
- Results persist as `EvaluationRun` rows so quality can be tracked over time.

### 3.11 Observability
- **Structured logging** via `structlog` — every request gets a `request_id`
  bound into the log context; downstream lines all carry it.
- **Prometheus metrics** — request count, latency histograms, per-route status,
  ingestion timings.
- **OpenTelemetry** traces exported via OTLP.
- **Langfuse** integration for LLM-call tracing (prompt/response/cost).
- A `/metrics` endpoint and a `/healthz` endpoint are always available.

### 3.12 Admin
- **Analytics overview** — doc counts, chunk counts, ingestion success rate,
  retrieval and answer-latency percentiles, top queries.
- Reserved for users with the `owner` or `admin` role.

### 3.13 Code editor & AI inline assist
A small **Monaco-style editor** is included for editable text/markdown documents
(view + save). It also exposes an `/assist/complete` endpoint backed by the chat
LLM for inline completion suggestions.

---

## 4. Technical stack — every layer

### 4.1 Backend
| Concern | Technology |
|---|---|
| Web framework | **FastAPI** (Python 3.12) |
| ASGI server | **Uvicorn** (with `uvloop`, `httptools` in production) |
| ORM | **SQLAlchemy 2.0 async** |
| Migrations | **Alembic** |
| Validation | **Pydantic v2** + `pydantic-settings` |
| Auth | **PyJWT**, **passlib[argon2]**, **Authlib** (OIDC) |
| Background jobs | **Celery** + Redis (production); **inline asyncio task** in LITE_MODE |
| WebSockets | FastAPI built-in (Starlette) |
| Logging | **structlog** |
| HTTP client | **httpx** (async) |
| File uploads | **python-multipart** |
| Email validation | **email-validator** |

### 4.2 Data layer
| Concern | Technology |
|---|---|
| Relational DB | **PostgreSQL** (asyncpg driver) |
| Connection in production | **Neon** (serverless, SSL-required) |
| Vector DB | **Qdrant** (production) / in-memory (LITE_MODE) |
| Graph DB | **Neo4j** (production) / in-memory (LITE_MODE) |
| Object storage | **S3-compatible / MinIO** (production) / in-memory (LITE_MODE) |
| Cache / queue broker | **Redis** (production) |

### 4.3 AI / ML
| Concern | Technology |
|---|---|
| LLM providers | **Ollama** (default local), **OpenAI-compatible** (Groq, OpenAI, vLLM, etc.), **Fake** (deterministic stub) |
| Default cloud chat model | **`llama-3.3-70b-versatile`** via Groq |
| Embeddings | **Ollama**, **SentenceTransformers**, **OpenAI-compatible**, **Fake** |
| Reranker | Cross-encoder (`BAAI/bge-reranker-base`) in production; null in LITE_MODE |
| Agent framework | **LangGraph**-style supervisor (in-house implementation) |
| Tracing | **Langfuse** |

### 4.4 Document parsing
| Format | Library |
|---|---|
| PDF (text) | **PyMuPDF (fitz)** |
| PDF (scanned) | PyMuPDF + **Tesseract OCR** (`pytesseract`) |
| DOCX | **python-docx** |
| Plain text / Markdown | native |
| HTML | text extraction via standard parsers |
| Images | Tesseract OCR |

### 4.5 Frontend
| Concern | Technology |
|---|---|
| Framework | **React 18** + **TypeScript** |
| Build tool | **Vite** |
| Styling | **Tailwind CSS** + **shadcn/ui** components |
| State (server) | **TanStack Query** (React Query) |
| State (client) | **Zustand** |
| Routing | **React Router** |
| Editor | **Monaco** (lazy-loaded) |
| HTTP | typed fetch wrapper with one-shot 401 → refresh |
| WebSocket | native browser API with auto ws/wss scheme switch |

### 4.6 DevOps & observability
| Concern | Technology |
|---|---|
| Container builds | **Docker** + **docker-compose** for local |
| Orchestration | **Kubernetes** + **Helm** charts |
| Reverse proxy | **Nginx** (in K8s) |
| CI | **GitHub Actions** |
| Metrics | **Prometheus** + **Grafana** |
| Logs | **Loki** |
| Traces | **OpenTelemetry** → Tempo/Jaeger |
| LLM tracing | **Langfuse** |

### 4.7 Free-tier hosts
| Concern | Service |
|---|---|
| Backend | **Render** (Web Service, free plan) |
| Frontend | **Vercel** (Hobby plan) |
| Postgres | **Neon** (free serverless) |
| LLM | **Groq** (free OpenAI-compatible API) |

---

## 5. How it works — request lifecycles

### 5.1 Document upload
```
client                  FastAPI                Postgres / Storage     Background pipeline
  │  POST /documents      │                          │                       │
  │  ───────────────────► │                          │                       │
  │                       │  hash(file) → dedupe     │                       │
  │                       │ ───────────────────────► │                       │
  │                       │  put_object(raw bytes)   │                       │
  │                       │ ───────────────────────► │                       │
  │                       │  insert Document row     │                       │
  │                       │ ───────────────────────► │                       │
  │                       │  enqueue_ingestion(id)   │                       │
  │                       │ ────────────────────────────────────────────────►│
  │ ◄──── 201 + doc ─────┤                          │                       │
  │ poll /documents/.../  │                          │                       │
  │       status          │                          │            PARSE     │
  │                       │                          │           METADATA   │
  │                       │                          │            CHUNK     │
  │                       │                          │            INDEX     │
  │                       │                          │            GRAPH     │
  │                       │                          │  update status=INDEXED│
```

### 5.2 Search
```
POST /search { query, top_k, strategy: "hybrid" }
   │
   ├─ BM25 retriever        (Postgres FTS, top_k)
   ├─ Dense retriever       (vector store, top_k)
   ├─ Reciprocal Rank Fusion (combines the two lists)
   ├─ Optional reranker     (cross-encoder, null in LITE_MODE)
   └─ Return hits           (chunk_id, document_id, content, score, source, page)
```

### 5.3 RAG query (`POST /rag/query`)
```
1. Retrieve top-k chunks (same as Search).
2. Build prompt: system instruction + numbered context chunks + user question.
3. Call LLM provider (Groq in deploy, Ollama local).
4. Parse citations [1], [2], ... from the answer; map them back to chunks.
5. Return { answer, citations }.
```

### 5.4 Streaming chat (`WS /chat/...`)
```
1. WebSocket opens with bearer token in querystring.
2. Server attaches to a conversation, loads recent messages as memory.
3. On user message:
     a. Retrieve relevant chunks (workspace-scoped).
     b. Build prompt with memory + retrieved context.
     c. Stream LLM tokens back to the client as they arrive.
     d. After completion, persist the assistant message + citation references.
```

### 5.5 Multi-agent research (`POST /agents/research`)
```
Decomposer  ─► [sub-query 1, sub-query 2, ...]
              │
              ▼
   ┌──────────────────────┐
   │ Researcher  (parallel)│  retrieval per sub-query
   └──────────────────────┘
              │
              ▼
   ┌──────────────────────┐
   │ Verifier              │  drops claims that aren't supported
   └──────────────────────┘
              │
              ▼
   ┌──────────────────────┐
   │ Synthesizer           │  writes the final cited answer
   └──────────────────────┘
```

---

## 6. Project structure

### 6.1 Top-level
```
.
├── backend/                   FastAPI service, Alembic migrations, tests
├── frontend/                  Vite + React SPA
├── docs/                      Architecture deep-dives + free-deploy guide
├── scripts/                   e2e_probe.py — live end-to-end check
├── infra/                     Helm charts, K8s manifests, Compose files
├── render.yaml                Render Blueprint (auto-deploys backend)
├── enterprise_rag.bat         Windows one-click: full Docker stack
├── enterprise_rag_demo.bat    Windows one-click: lightest demo mode
└── Rag_Project_Details.md     (this file)
```

### 6.2 Backend layout (`backend/app/`)
Clean architecture, one folder per **domain**, each with `models/`, `schemas/`,
`repositories/`, `services/`.

```
app/
├── core/              config, logging, middleware, exceptions, metrics, ratelimit, security primitives
├── api/v1/routes/     thin HTTP handlers — auth, documents, search, rag, chat, graph, agents, workspaces, evaluation, admin, assist, oauth, health, users
├── db/                SQLAlchemy base, session factory, Alembic migrations
├── domains/
│   ├── identity/        users, orgs, roles, permissions
│   ├── documents/       Document + IngestionJob models, upload service
│   ├── ingestion/       parsers (pdf, docx, html, image, text), pipeline orchestrator, task bus
│   ├── chunking/        5 chunking strategies + tokenizer
│   ├── embeddings/      embedding service + version tracking
│   ├── retrieval/       BM25, dense, hybrid retrievers; RRF fusion; retrieval logs
│   ├── rag/             RAG engine, prompt assembly, citation extraction
│   ├── chat/            conversations, messages, memory summarization, WS handler
│   ├── workspaces/      per-workspace document sets and config
│   ├── graphrag/        rule-based + LLM entity extractors, graph builder, graph retrieval
│   ├── agents/          decomposer, researcher, verifier, synthesizer
│   ├── evaluation/      datasets, runs, metrics
│   ├── security/        password hashing, OAuth flows
│   └── observability/   analytics service
├── integrations/      provider abstractions (Protocol + factory per concern)
│   ├── llm/             ollama, openai-compatible, fake
│   ├── embeddings/      ollama, sentence_transformers, openai, fake
│   ├── vectorstore/     qdrant, memory
│   ├── graphstore/      neo4j, memory
│   ├── storage/         s3/minio, memory
│   ├── ocr/             tesseract, null
│   ├── reranker/        cross-encoder, null
│   └── cache/           embedding cache
└── workers/           Celery app + task definitions
```

### 6.3 Frontend layout (`frontend/src/`)
```
src/
├── features/         one folder per feature — auth, documents, search, chat, graph, agents, evaluation, workspaces, admin
├── components/       shared UI (Badge, ErrorText, layout primitives)
├── lib/              api.ts (typed client), ws.ts (WebSocket helper), auth store
├── types/            generated/typed API DTOs
└── vite-env.d.ts     Vite env typings (VITE_API_BASE, VITE_API_PROXY)
```

---

## 7. Configuration

All settings load from **environment variables** via Pydantic, grouped into
nested models. The most important ones:

### 7.1 Mode flags (free-tier shape)
| Variable | What it does |
|---|---|
| `ENVIRONMENT` | `local` / `test` / `staging` / `production` |
| `LITE_MODE=true` | In-memory storage/vector/graph + null OCR/reranker + rule-based graph extractor. Free-tier essentials. |
| `INGESTION_INLINE=true` | Run the ingestion pipeline in the request process. No Celery / Redis broker needed. |
| `DEBUG=false` | Disable verbose logs |
| `RATE_LIMIT_PER_MINUTE=120` | Per-client RPS cap |

### 7.2 Database
| Variable | Notes |
|---|---|
| `DATABASE_URL` | Full Postgres connection string (e.g. Neon). Schemes `postgresql://` and `postgres://` both work. Libpq-only params (`sslmode`, `channel_binding`, `application_name`, …) are stripped automatically; SSL is enabled on the asyncpg side. |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Per-field fallback when `DATABASE_URL` is unset (local dev). |

### 7.3 Auth
| Variable | Notes |
|---|---|
| `AUTH_SECRET_KEY` | JWT signing secret (auto-generated on Render). |
| `AUTH_ALGORITHM` | Default `HS256`. Use `RS256` in production with keypair. |
| `AUTH_GOOGLE_CLIENT_ID/SECRET`, `AUTH_MICROSOFT_CLIENT_ID/SECRET` | OIDC SSO (optional). |
| `AUTH_SSO_REDIRECT_URL` | Where the OAuth callback forwards the token pair. |

### 7.4 LLM (chat answers)
| Variable | Notes |
|---|---|
| `LLM_PROVIDER` | `ollama` (default), `openai`, `vllm`, `fake` |
| `LLM_BASE_URL` | Provider HTTP endpoint. Accepts forms **with or without** trailing `/v1` (Groq + OpenAI SDK convention both work). |
| `LLM_API_KEY` | Provider API key. |
| `LLM_CHAT_MODEL` | Model id (e.g. `llama-3.3-70b-versatile` on Groq, `llama3.1:8b` on Ollama). |

### 7.5 Embeddings
| Variable | Notes |
|---|---|
| `LLM_EMBEDDING_PROVIDER` | `ollama` / `sentence_transformers` / `openai` / `fake` |
| `LLM_EMBEDDING_MODEL` | Model id. |
| `LLM_EMBEDDING_DIM` | Vector dim. Must match the model. |

### 7.6 CORS
| Variable | Notes |
|---|---|
| `CORS_ORIGINS` | Allowed origins. Accepts **bare URL**, **comma-separated list**, or **JSON array**. Empty = none allowed. |

### 7.7 Vector / Graph / Storage (only used when not LITE_MODE)
`QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_PREFIX`
`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
`STORAGE_ENDPOINT_URL`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET`

### 7.8 Observability
`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`
`OTEL_LANGFUSE_PUBLIC_KEY`, `OTEL_LANGFUSE_SECRET_KEY`, `OTEL_LANGFUSE_HOST`

### 7.9 Frontend (Vite)
| Variable | Notes |
|---|---|
| `VITE_API_BASE` | Absolute backend URL (no trailing slash). Production only — leave blank for local dev. |
| `VITE_API_PROXY` | Backend URL the dev-server proxies `/api` to. Local dev only. |

---

## 8. Running it

Three ways, ordered by weight:

### 8.1 Demo mode (lightest — recommended for laptops)
Native Python + a single Postgres container. Fake LLM/embeddings, in-memory
vector/graph, inline ingestion. **No Redis / Qdrant / Neo4j / Ollama / worker
needed.**

Windows: double-click **`enterprise_rag_demo.bat`**.

Then open **http://localhost:5173**. Register, upload a `.txt`/`.md` file →
search → chat. Retrieval, chunking, citations, graph, and agents are all real;
only LLM/embeddings are stubbed.

### 8.2 Full local stack
Native Docker Compose: api, worker, postgres, redis, qdrant, minio, ollama,
neo4j, prometheus, grafana, loki.

Windows: double-click **`enterprise_rag.bat`** (needs ~10 GB RAM + a one-time
`ollama pull` of the chat/embedding models).

Or by hand:
```bash
docker compose up -d                    # everything
# … or selectively …
docker compose up -d postgres redis qdrant minio
cp backend/.env.example backend/.env
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload           # http://localhost:8000/docs
cd ../frontend
npm install
npm run dev                             # http://localhost:5173
```

### 8.3 Free cloud deploy
Vercel (frontend) + Render (backend) + Neon (Postgres) + Groq (LLM).
Step-by-step in [`docs/DEPLOY_FREE.md`](docs/DEPLOY_FREE.md). Includes
`render.yaml` Blueprint and `frontend/vercel.json`. Auto-deploys on every push
to `main`.

---

## 9. Testing

### 9.1 Unit tests
```bash
cd backend
pytest tests/unit -q
```
Covers config parsing, security primitives, retrieval fusion, chunking, parsers,
provider mocks. 59 tests, runs in ~2 seconds.

### 9.2 Integration tests
```bash
pytest tests/integration -q
```
Hits a real Postgres (testcontainers / docker compose) — full ingestion +
retrieval + RAG flow.

### 9.3 End-to-end probe (live deploy)
```bash
python scripts/e2e_probe.py
```
Hits the deployed backend at the URL hard-coded in the script. Runs
**24 checks**: health, auth, upload, ingestion (all 5 stages), workspaces,
search (hybrid/dense/bm25), RAG with real LLM, chat conversations, graph
explore, agent research, evaluation list, admin analytics, cleanup. Prints a
PASS/FAIL summary.

---

## 10. Deployment shape (the choices that matter on the free tier)

The free-tier deploy makes some intentional trade-offs (documented in
`docs/DEPLOY_FREE.md`):

| Pillar | Free tier choice | Full / Production |
|---|---|---|
| Storage | In-memory `LITE_MODE` | S3 / MinIO |
| Vector | In-memory | Qdrant cluster |
| Graph | In-memory + rule-based extractor | Neo4j + LLM extractor |
| OCR | Null (text-based PDFs only) | Tesseract / PaddleOCR |
| Reranker | Null (RRF only) | Cross-encoder |
| Embeddings | Fake (BM25 + Postgres FTS carries quality) | SentenceTransformers / OpenAI-compatible |
| Chat LLM | Groq (real, free) | Groq / OpenAI / vLLM / Ollama |
| Ingestion runner | Inline (`INGESTION_INLINE=true`) | Celery + Redis broker + workers |
| Postgres | Neon free serverless | Self-hosted / RDS / Cloud SQL |

Cold-start on the free Render dyno is ~30–60 s after 15 min idle; subsequent
requests are fast. Vectors and the graph reset on dyno restart since they're
in-memory — Postgres chunks persist, so BM25 search keeps working, and a
re-upload restores dense retrieval.

---

## 11. Where to go next

| Topic | Document |
|---|---|
| System architecture & request lifecycles | [docs/architecture/01-system-architecture.md](docs/architecture/01-system-architecture.md) |
| Infrastructure & runtime topology | [docs/architecture/02-infrastructure-architecture.md](docs/architecture/02-infrastructure-architecture.md) |
| Monorepo layout & conventions | [docs/architecture/03-monorepo-structure.md](docs/architecture/03-monorepo-structure.md) |
| Backend layers, DI, persistence | [docs/architecture/04-backend-architecture.md](docs/architecture/04-backend-architecture.md) |
| Frontend architecture | [docs/architecture/05-frontend-architecture.md](docs/architecture/05-frontend-architecture.md) |
| PostgreSQL schema | [docs/architecture/06-database-schema.md](docs/architecture/06-database-schema.md) |
| AI / RAG / agent pipelines | [docs/architecture/07-ai-pipeline-architecture.md](docs/architecture/07-ai-pipeline-architecture.md) |
| Build, K8s/Helm, CI/CD, scaling | [docs/architecture/08-deployment-architecture.md](docs/architecture/08-deployment-architecture.md) |
| Free-tier deployment walkthrough | [docs/DEPLOY_FREE.md](docs/DEPLOY_FREE.md) |

---

## 12. Glossary

| Term | Meaning |
|---|---|
| **RAG** | Retrieval-Augmented Generation — retrieve relevant chunks, then have an LLM answer the question grounded in those chunks. |
| **Chunk** | A bounded slice of a document that gets embedded + indexed independently. |
| **BM25** | Classical lexical / keyword ranking algorithm (TF-IDF family). |
| **Dense retrieval** | Embedding-based nearest-neighbour search. |
| **Hybrid retrieval** | Combine BM25 + dense; the platform uses Reciprocal Rank Fusion (RRF). |
| **Reranker** | A second-stage model (cross-encoder) that re-orders the top-k for better precision. |
| **Knowledge graph** | Entities + typed relations extracted from text, queried by k-hop traversal. |
| **Workspace** | A scoping unit for documents within an organization. |
| **Multi-tenancy** | One deployment, many orgs, hard-isolated data. |
| **LITE_MODE** | Free-tier shape — in-memory infra, null OCR/reranker, rule-based graph, deterministic embeddings. Real LLM + real Postgres still used. |
