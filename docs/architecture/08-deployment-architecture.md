# 08 — Deployment Architecture

## 1. Build & image strategy

- Multi-stage Dockerfiles (`infra/docker/`): `backend.Dockerfile` (api + worker share a
  base image, differ by entrypoint), `frontend.Dockerfile` (Vite build → Nginx static).
- Non-root users, pinned base images, `pip`/`uv` with locked deps, SBOM + vuln scan
  (Trivy) in CI. Images tagged by git SHA + semver.

## 2. Local — docker-compose

`docker-compose.yml` brings up the full stack: `api`, `worker`, `beat`, `postgres`,
`redis`, `qdrant`, `neo4j`, `minio`, `ollama`, `otel-collector`, `prometheus`,
`grafana`, `loki`, `langfuse`, `frontend`. One command to a working platform.

## 3. Kubernetes (staging/prod) — Helm

`infra/helm/enterprise-rag/` chart with templates:

- `api` Deployment + Service + HPA (CPU + latency) + PDB.
- `worker` Deployments per queue (`ocr/parse/chunk/embed/index/graph/eval`), each with
  its own HPA (queue depth via KEDA optional); GPU node-pool tolerations for `embed`/`ocr`.
- `beat` (single replica), Ingress (Nginx + cert-manager TLS), ConfigMaps, Secrets.
- Stateful deps (`postgres`, `redis`, `qdrant`, `neo4j`, `minio`) via subcharts or
  managed services in prod; values toggle in-cluster vs external.
- `values-{local,staging,prod}.yaml` per environment.

## 4. CI/CD — GitHub Actions

```
lint (ruff) + type (mypy) + frontend lint/types
        │
unit + integration + e2e tests  ──▶ coverage gate
        │
build images ──▶ Trivy scan ──▶ push to registry
        │
helm upgrade --install (staging)  ──▶ smoke tests
        │
manual approval ──▶ helm upgrade (prod, canary/rolling)
```

DB migrations run as a pre-deploy Kubernetes Job (`alembic upgrade head`) gated before
the new app version receives traffic.

## 5. Scaling model

- **API**: stateless, HPA on CPU + p95 latency; pgbouncer in front of Postgres.
- **Workers**: scale per queue independently on queue depth; embedding/OCR on GPU pool.
- **Qdrant**: sharded collections + replication; per-tenant collections for high tiers.
- **Postgres**: primary + read replicas; partition high-volume log tables; archive cold.
- **Redis**: cluster mode for cache + broker separation (or separate instances).

## 6. Observability in prod

- OTel Collector sidecar/daemonset → Tempo (traces), Prometheus (metrics), Loki (logs);
  Grafana dashboards (API latency, queue depth, retrieval latency, token/cost, eval
  scores). Langfuse for LLM/agent traces. Alertmanager rules on SLOs + error budgets.

## 7. Hardening checklist (prod)

- Secrets from Vault/External Secrets; no secrets in images or git.
- NetworkPolicies default-deny; only Nginx public.
- TLS everywhere (ingress + internal mTLS optional via mesh).
- Encryption at rest (DB, object store SSE-KMS, Qdrant/Neo4j volumes).
- Pod security: non-root, read-only rootfs, dropped caps, resource limits.
- Backups + restore drills; PITR for Postgres; snapshot schedules for Qdrant/Neo4j.
- Audit logging on; rate limits + WAF at edge.

## 8. Rollback

- Versioned images + Helm release history → `helm rollback`.
- Migrations are forward-compatible (expand/contract) so app rollback doesn't break the
  schema; destructive migrations split across releases.
