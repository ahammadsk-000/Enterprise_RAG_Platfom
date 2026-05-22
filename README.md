# Enterprise RAG Platform

A production-grade, multi-tenant Retrieval-Augmented Generation platform for
enterprise knowledge — document ingestion + OCR, hybrid + graph retrieval, agentic
reasoning, citation-grounded streaming answers, evaluation, and full observability.
Built FastAPI-first with clean architecture, async-everywhere, and Kubernetes-ready
deployment.

> Status: **Phase 2 — document ingestion** complete (auth/RBAC/SSO + ingestion
> pipeline). See the roadmap below and the design docs in
> [`docs/architecture/`](docs/architecture/).

## Architecture

| Doc | Topic |
|-----|-------|
| [01](docs/architecture/01-system-architecture.md) | System architecture & request lifecycles |
| [02](docs/architecture/02-infrastructure-architecture.md) | Infrastructure & runtime topology |
| [03](docs/architecture/03-monorepo-structure.md) | Monorepo layout & conventions |
| [04](docs/architecture/04-backend-architecture.md) | Backend layers, DI, persistence |
| [05](docs/architecture/05-frontend-architecture.md) | Frontend architecture |
| [06](docs/architecture/06-database-schema.md) | PostgreSQL schema |
| [07](docs/architecture/07-ai-pipeline-architecture.md) | AI/RAG/agent pipelines |
| [08](docs/architecture/08-deployment-architecture.md) | Build, K8s/Helm, CI/CD, scaling |

## Tech stack

**Backend** FastAPI · Python 3.12 · async SQLAlchemy 2 · Alembic · PostgreSQL ·
Redis · Celery · WebSockets · JWT/OAuth2/RBAC
**AI/ML** LangChain · LangGraph · Ollama (default) / vLLM / OpenAI-compatible ·
SentenceTransformers · Qdrant · Neo4j
**Docs** PyMuPDF · pdfplumber · Unstructured · Tesseract/PaddleOCR
**Frontend** React · TypeScript · Vite · Tailwind · shadcn/ui · Zustand · React Query
**DevOps/Obs** Docker · Compose · Kubernetes · Helm · GitHub Actions · Nginx ·
Prometheus · Grafana · Loki · OpenTelemetry · Langfuse

## Quick start (local)

```bash
# 1. bring up the full stack (db, redis, qdrant, neo4j, minio, ollama, api, worker, obs)
docker compose up -d postgres redis qdrant minio
cp backend/.env.example backend/.env

# 2. backend dev loop
cd backend
pip install -e ".[dev]"
alembic upgrade head            # (migrations land with the identity domain in Phase 1b)
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 3. tests
pytest
```

Or run everything containerized: `docker compose up -d` then open
`http://localhost:8000/docs` (API) and `http://localhost:5173` (frontend).

## Roadmap

1. **Phase 1** — Architecture, monorepo, backend core, **auth/RBAC/multi-tenancy** ← current
2. Phase 2 — Document ingestion + OCR + metadata extraction
3. Phase 3 — Chunking, embeddings, Qdrant integration
4. Phase 4 — Hybrid retrieval, RAG engine, citations
5. Phase 5 — Streaming chat, conversation memory, workspaces
6. Phase 6 — Graph RAG (Neo4j knowledge graph)
7. Phase 7 — Multi-agent retrieval (LangGraph)
8. Phase 8 — Evaluation & hallucination detection
9. Phase 9 — Observability (OTel/Prometheus/Grafana/Loki/Langfuse)
10. Phase 10 — Kubernetes/Helm, hardening, production scaling

## Repository layout

See [`docs/architecture/03-monorepo-structure.md`](docs/architecture/03-monorepo-structure.md).
