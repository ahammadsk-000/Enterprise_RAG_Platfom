# 06 — Database Schema (PostgreSQL system of record)

Conventions: UUID v7 PKs, `created_at`/`updated_at` (tz-aware), soft-delete via
`deleted_at` where useful, **every tenant-owned table carries `organization_id`**.
Vectors live in Qdrant and the graph in Neo4j; Postgres holds the authoritative
metadata and provenance that ties them together.

## Entity-relationship overview

```
organizations 1───* workspaces 1───* documents 1───* chunks
      │                  │               │
      │                  │               └─* citations *─── messages
      │                  │
      │                  └─* memberships *─── users
      │                  └─* conversations 1─* messages
      └─* users  └─* api_keys  └─* audit_logs  └─* roles/permissions
documents 1─* ingestion_jobs        chunks ─(provenance)→ kg_entities (Neo4j)
retrieval_logs *── conversations     embedding_versions 1─* chunks
```

## Core tables

### Identity & tenancy
- **organizations** `(id, name, slug, plan, settings jsonb, created_at, ...)`
- **users** `(id, email unique, full_name, hashed_password nullable, auth_provider,
  is_active, is_superuser, last_login_at, ...)`
- **roles** `(id, organization_id, name, scope[org|workspace], is_system)`
- **permissions** `(id, code unique)` — e.g. `documents:write`, `workspace:admin`
- **role_permissions** `(role_id, permission_id)`
- **memberships** `(id, organization_id, workspace_id nullable, user_id, role_id,
  status)` — a user's role within an org and optionally a specific workspace
- **api_keys** `(id, organization_id, user_id, name, prefix, hashed_secret,
  scopes jsonb, last_used_at, expires_at, revoked_at)`
- **oauth_accounts** `(id, user_id, provider, provider_account_id, ...)`

### Workspaces
- **workspaces** `(id, organization_id, name, slug, description, settings jsonb,
  default_embedding_version_id, default_llm_model, created_by, ...)`
- **workspace_settings** (or embedded jsonb): retrieval defaults, chunking strategy,
  guardrail policy.

### Documents & ingestion
- **documents** `(id, organization_id, workspace_id, title, source_uri,
  storage_key, mime_type, byte_size, content_hash unique-per-ws, language,
  page_count, status[UPLOADED|PARSING|PARSED|CHUNKING|CHUNKED|EMBEDDING|INDEXED|FAILED],
  error, metadata jsonb, created_by, ...)`
- **ingestion_jobs** `(id, document_id, stage, status, attempts, started_at,
  finished_at, worker, payload jsonb, error)` — one row per pipeline stage run
- **chunks** `(id, organization_id, workspace_id, document_id, ordinal,
  parent_chunk_id nullable, content, content_hash, token_count, page_from, page_to,
  bbox jsonb, chunk_type[text|table|code|caption], embedding_version_id,
  vector_id (Qdrant point id), metadata jsonb)`
- **embedding_versions** `(id, model_name, dim, normalize, provider, params jsonb,
  created_at)` — enables embedding versioning + incremental reindex

### Conversations & RAG
- **conversations** `(id, organization_id, workspace_id, user_id, title,
  model, system_prompt, memory_strategy, created_at, last_message_at)`
- **messages** `(id, conversation_id, role[user|assistant|system|tool], content,
  token_usage jsonb, latency_ms, model, finish_reason, faithfulness_score,
  confidence, parent_message_id, created_at)`
- **citations** `(id, message_id, chunk_id, document_id, page, bbox jsonb,
  score, snippet, rank)` — grounds each answer to retrieved evidence
- **retrieval_logs** `(id, organization_id, workspace_id, conversation_id nullable,
  query, expanded_query, strategy, k, latency_ms, dense_hits jsonb, bm25_hits jsonb,
  reranked jsonb, fused_scores jsonb, created_at)` — analytics + eval (partition by month)

### Memory
- **memories** `(id, organization_id, scope[user|workspace|conversation], owner_id,
  kind[fact|summary|preference], content, embedding_version_id, vector_id,
  salience, expires_at, created_at)` — long-term/user/workspace memory

### Agents
- **agent_runs** `(id, organization_id, workspace_id, conversation_id nullable,
  graph_name, status, input jsonb, output jsonb, total_tokens, cost, started_at,
  finished_at)`
- **agent_steps** `(id, agent_run_id, ordinal, node_name, role[planner|retriever|
  verifier|summarizer|citation|research], input jsonb, output jsonb, tokens,
  latency_ms, trace_id)`

### Knowledge graph provenance (Neo4j is authoritative for the graph)
- **kg_entities** `(id, organization_id, workspace_id, neo4j_id, name, type,
  canonical_name, embedding_version_id, vector_id)`
- **kg_mentions** `(id, entity_id, chunk_id, document_id, span jsonb, confidence)`
  — links graph nodes back to source chunks for citations
- **kg_relations** `(id, organization_id, source_entity_id, target_entity_id,
  type, confidence, evidence_chunk_id)`

### Evaluation
- **eval_datasets** `(id, organization_id, workspace_id, name, kind)`
- **eval_samples** `(id, dataset_id, question, ground_truth, contexts jsonb)`
- **eval_runs** `(id, dataset_id, config jsonb, metrics jsonb[faithfulness,
  answer_relevancy, context_precision, context_recall], created_at)`
- **eval_results** `(id, eval_run_id, sample_id, answer, scores jsonb,
  retrieved jsonb)`

### Security & governance
- **audit_logs** `(id, organization_id, actor_user_id, action, resource_type,
  resource_id, ip, user_agent, metadata jsonb, created_at)` — append-only, partitioned
- **pii_findings** `(id, organization_id, document_id|message_id, type, span jsonb,
  action[masked|flagged], created_at)`

## Indexing & partitioning notes
- Composite indexes on `(organization_id, workspace_id, ...)` for tenant-scoped reads.
- `content_hash` indexes for duplicate detection.
- `retrieval_logs`, `audit_logs`, `agent_steps` partitioned by month (high volume).
- `messages(conversation_id, created_at)` for chat pagination.
- Qdrant payload mirrors `(organization_id, workspace_id, document_id, embedding_version_id)`
  for filtered search; Postgres `chunks.vector_id` is the join key.
