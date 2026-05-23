# Enterprise RAG — Frontend

React + TypeScript + Vite + TailwindCSS + Zustand + React Query SPA for the
Enterprise RAG Platform.

## Features (current)

- **Auth** — register (creates an org + owner) / login, JWT with silent refresh
- **Documents** — drag-to-upload, ingestion status (auto-polling), reindex, delete
- **Search** — hybrid / dense / BM25 retrieval with re-ranking toggle
- **Chat** — citation-grounded RAG answers with confidence, sources, and token usage

## Run

```bash
cd frontend
cp .env.example .env          # optional: set VITE_API_PROXY if backend isn't on :8000
npm install
npm run dev                   # http://localhost:5173
```

The dev server **proxies `/api` to the backend** (default `http://localhost:8000`),
so the backend must be running. There is no CORS to configure in dev.

> Heads-up: the UI needs the backend up. The fastest way to get a working backend for
> a click-through is "demo mode" (in-memory providers + a deterministic fake LLM +
> inline ingestion) — see the backend README / ask to have it wired.

## Structure

```
src/
├── lib/api.ts        # typed fetch client (bearer auth + one-shot refresh)
├── stores/auth.ts    # Zustand auth/session store
├── types/api.ts      # TS mirror of backend Pydantic schemas
├── components/       # Layout + Tailwind UI primitives
└── features/         # auth · documents · search · chat
```

## Build

```bash
npm run build         # tsc type-check + vite production build → dist/
```
