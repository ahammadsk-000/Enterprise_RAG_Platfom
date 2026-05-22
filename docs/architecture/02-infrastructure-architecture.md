# 02 — Infrastructure Architecture

## 1. Runtime topology

| Plane | Components | Notes |
|-------|-----------|-------|
| **Edge** | Nginx Ingress (TLS termination, gzip, rate-limit, sticky WS) | cert-manager for ACME |
| **App** | FastAPI (Uvicorn/Gunicorn, N replicas), stateless | HPA on CPU + req latency |
| **Async** | Celery workers by queue: `ocr`, `parse`, `chunk`, `embed`, `index`, `graph`, `eval`; Celery Beat for schedules | GPU node-pool for `embed`/`ocr` |
| **Realtime** | WebSocket gateway (same app, sticky sessions) | Redis pub/sub fan-out for multi-replica |
| **Data** | PostgreSQL (HA primary + replica, pgbouncer), Redis (cache+broker), Qdrant (sharded), Neo4j, Object store (S3/MinIO) | |
| **Observability** | OTel Collector → Tempo, Prometheus, Loki, Grafana, Langfuse | |

## 2. Environments

- **local** — `docker-compose` brings up everything: api, worker, postgres, redis,
  qdrant, neo4j, minio, ollama, otel-collector, prometheus, grafana, loki, langfuse.
- **staging / production** — Kubernetes via Helm (`infra/helm/enterprise-rag`),
  values per environment, secrets from external secret manager (Vault/SealedSecrets).

## 3. Networking & isolation

- Internal services on a private network; only Nginx is internet-facing.
- NetworkPolicies restrict pod-to-pod traffic to declared dependencies.
- Per-tenant data isolation is logical (row + payload scoping), with an option for
  per-tenant Qdrant collections / Neo4j databases for high-isolation tiers.

## 4. Storage strategy

| Store | Holds | Scaling |
|-------|-------|---------|
| PostgreSQL | system of record: users, orgs, workspaces, documents, conversations, messages, citations, audit, api keys, retrieval logs | read replicas, partition large log tables by month |
| Qdrant | chunk vectors + payload (tenant, workspace, doc, page, hash) | collection sharding + replication, HNSW tuned per collection |
| Neo4j | entities, relations, mentions, doc/chunk provenance | causal cluster for HA |
| Redis | cache, Celery broker/result, rate limits, WS pub/sub, sessions | cluster mode |
| Object store | raw uploads, rendered page images, OCR artifacts, exports | lifecycle rules, SSE-KMS |

## 5. Secrets & config

- 12-factor: all config via env / mounted secrets; nothing sensitive in images.
- `.env.example` documents every variable; `Settings` validates at boot (fail-fast).
- Production secrets via Kubernetes Secrets sourced from Vault/External Secrets.

## 6. Resilience

- Health (`/healthz`) and readiness (`/readyz`) probes gate traffic.
- Graceful shutdown drains in-flight requests + WS connections.
- Celery tasks are idempotent with retries + exponential backoff + dead-letter queue.
- Circuit breakers / timeouts around every external provider call.
- Backups: nightly `pg_dump` + WAL archiving; Qdrant + Neo4j snapshots; object-store
  versioning.

## 7. GPU & inference

- Embedding/OCR/reranker workloads target a GPU node pool (taints/tolerations).
- LLM inference: Ollama (local/dev) or vLLM (prod) behind an OpenAI-compatible adapter,
  selectable per-tenant/model via the provider registry.
