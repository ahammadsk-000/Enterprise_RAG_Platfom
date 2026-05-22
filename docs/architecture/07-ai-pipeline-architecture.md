# 07 — AI Pipeline Architecture

## 1. Provider abstraction

All AI capabilities sit behind interfaces in `integrations/` so providers are swappable
per tenant/workspace via the provider registry + `Settings`:

| Capability | Interface | Default | Alternatives |
|-----------|-----------|---------|--------------|
| LLM (chat/stream) | `LLMProvider` | Ollama | vLLM, OpenAI-compatible |
| Embeddings | `EmbeddingProvider` | Ollama / SentenceTransformers | OpenAI |
| Reranker | `Reranker` | cross-encoder (HF) | Cohere-compatible |
| Vector store | `VectorStore` | Qdrant | — |
| Graph store | `GraphStore` | Neo4j | — |
| OCR | `OCREngine` | Tesseract | PaddleOCR |
| Object storage | `ObjectStorage` | S3/MinIO | — |

## 2. Ingestion pipeline (event-driven, Celery)

```
upload ─▶ parse/OCR ─▶ chunk ─▶ embed ─▶ index(vector+bm25) ─▶ graph-extract ─▶ INDEXED
          │             │         │        │                    │
   layout-aware    strategy   versioned  Qdrant upsert     entities+relations→Neo4j
   PyMuPDF/Tika    chunkers   batched    + payload mirror   (+ kg provenance in PG)
   Tesseract/Paddle
```

- **Parse/OCR** — native text first; OCR fallback for scans; table + layout extraction
  (Unstructured/LayoutParser); language detection; page images rendered for previews.
- **Chunking strategies** (registry, configurable per workspace): semantic, recursive,
  parent-child (small child for recall, large parent for context), table-aware,
  code-aware, context-aware (heading/section enrichment).
- **Embedding** — batched, GPU-capable, **versioned** (`embedding_versions`); cached by
  `content_hash`; incremental reindex when a new version is selected.

## 3. Retrieval pipeline

```
query
  │  query expansion (optional, multi-query / HyDE)
  ▼
┌────────────┐   ┌─────────────┐
│ dense (ANN)│   │ BM25 keyword│      ── metadata filters (tenant/workspace/doc/type)
└─────┬──────┘   └──────┬──────┘
      └────── RRF fusion ┘
              │
        graph expansion (optional: pull neighbors of matched entities from Neo4j)
              │
        cross-encoder re-rank
              │
        context compression (dedupe, sentence-level pruning, token budgeting)
              ▼
        ranked, grounded context  ──▶  RAG engine
```

## 4. RAG engine

- Builds a **citation-constrained** prompt: the model must answer only from supplied
  context and emit citation markers mapped to `chunk_id`/`page`/`bbox`.
- **Grounding & hallucination control**: answerability check, "say I don't know" policy,
  per-claim citation requirement, optional self-consistency.
- **Confidence scoring**: from retrieval scores + reranker margins + verification.
- **Streaming**: tokens streamed over WS/SSE; citations resolved and attached on finish.
- Persists message, citations, token usage, latency, faithfulness score.

## 5. Agentic retrieval (LangGraph)

State-machine of specialized agents; each step persisted to `agent_steps` and traced:

```
        ┌─────────┐
        │ Planner │  decompose question → sub-questions / tool plan
        └────┬────┘
             ▼
        ┌──────────┐   ┌──────────┐
        │Retriever │──▶│Researcher│  iterative retrieval / web/doc tools
        └────┬─────┘   └────┬─────┘
             ▼               │
        ┌──────────┐         │
        │Summarizer│◀────────┘
        └────┬─────┘
             ▼
        ┌──────────┐    ┌───────────────────┐
        │ Verifier │──▶ │ Citation validator │  check claims ↔ evidence
        └────┬─────┘    └─────────┬──────────┘
             └──── grounded, cited answer ─────┘  (loop back if unverified)
```

- Orchestrated with **LangGraph** (typed state, conditional edges, retries).
- CrewAI/role-style agents available for research-heavy flows.
- Every node emits an OTel span + Langfuse generation; cost/tokens aggregated per run.

## 6. Graph RAG

- Entity + relation extraction during ingestion (LLM/NER) → Neo4j, with mention
  provenance back to chunks (`kg_mentions`).
- Retrieval can traverse the graph (k-hop neighborhood of seed entities) and fuse with
  vector hits — strong for multi-hop and "how is X related to Y" questions.

## 7. Multi-modal RAG

- Page images, charts, diagrams, screenshots embedded with a vision-language model;
  OCR + vision fusion so figures/tables are retrievable and citable alongside text.

## 8. Evaluation pipeline

- Metrics: faithfulness, answer relevancy, context precision/recall, hallucination rate.
- Runs over `eval_datasets`; results stored in `eval_runs`/`eval_results`; regression
  gates can run in CI against a golden set. Integrates with Phoenix/Langfuse for traces.

## 9. AI security in the pipeline

- **Prompt-injection defense**: input screening, instruction/firewall framing,
  tool-allowlist, output validation.
- **PII**: detection + masking before indexing and before sending context to external
  providers; findings recorded in `pii_findings`.
- **Content moderation** + **data-leakage prevention** applied at ingestion and response.
