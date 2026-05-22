# 03 — Monorepo Structure

```
Enterprise_RAG_Platform/
├── README.md
├── docker-compose.yml                # full local stack
├── .gitignore
├── .env.example                      # root-level shared env (compose)
│
├── docs/
│   ├── architecture/                 # 01..08 architecture docs (this set)
│   └── adr/                          # Architecture Decision Records
│
├── backend/
│   ├── pyproject.toml                # deps, ruff, mypy, pytest config
│   ├── alembic.ini
│   ├── .env.example
│   ├── README.md
│   ├── app/
│   │   ├── main.py                   # FastAPI app factory + lifespan
│   │   ├── core/                     # config, logging, security, exceptions, middleware
│   │   ├── db/                       # Base, async session, migrations/
│   │   ├── api/
│   │   │   ├── deps.py               # shared FastAPI dependencies (auth, tenant, db)
│   │   │   ├── v1/
│   │   │   │   ├── router.py         # aggregates all v1 routers
│   │   │   │   └── routes/           # health, auth, users, workspaces, documents, chat...
│   │   │   └── ws/                   # websocket endpoints (chat, ingestion progress)
│   │   ├── domains/                  # DDD bounded contexts (see below)
│   │   ├── integrations/             # provider adapters (llm, vectorstore, graphstore, ocr, storage)
│   │   ├── workers/                  # celery app + tasks
│   │   └── common/                   # shared value objects, pagination, result types
│   └── tests/ { unit, integration, e2e }
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts · tsconfig.json · tailwind.config.ts
│   ├── public/
│   └── src/
│       ├── app/                      # routing, providers, layout shells
│       ├── components/               # shared UI (shadcn/ui based)
│       ├── features/                 # auth, chat, documents, search, graph, admin
│       ├── lib/                      # api client, ws client, query client
│       ├── stores/                   # zustand stores
│       ├── hooks/ · types/ · styles/
│
├── infra/
│   ├── docker/                       # Dockerfiles (backend, worker, frontend)
│   ├── k8s/base/                     # raw manifests (kustomize base)
│   ├── helm/enterprise-rag/          # Helm chart (templates + values per env)
│   └── observability/                # prometheus, grafana, loki configs
│
├── .github/workflows/                # CI: lint, type, test, build, scan, deploy
└── scripts/                          # dev bootstrap, seed, migration helpers
```

## Backend domain layout (per bounded context)

Each domain follows the same internal shape so the codebase is predictable:

```
domains/<context>/
├── models/         # SQLAlchemy ORM entities (persistence)
├── schemas/        # Pydantic v2 DTOs (API + service contracts)
├── repositories/   # data-access interfaces + implementations
├── services/       # business logic (pure-ish, depends on repo interfaces)
└── __init__.py
```

Contexts: `identity`, `workspaces`, `documents`, `ingestion`, `chunking`,
`embeddings`, `retrieval`, `rag`, `chat`, `agents`, `graphrag`, `evaluation`,
`security`, `observability`.

## Conventions

- **Imports point inward.** `api/` → `domains/services` → `repositories (interfaces)`.
  Concretes (SQLAlchemy, Qdrant, Neo4j SDKs) live in `repositories/impl` and
  `integrations/`, wired via dependency injection in `api/deps.py` and worker setup.
- **One responsibility per file**; no module exceeds a sensible size.
- **Contracts in `schemas/`** are the only types crossing the API boundary.
- **Tests mirror the source tree** under `backend/tests/`.
