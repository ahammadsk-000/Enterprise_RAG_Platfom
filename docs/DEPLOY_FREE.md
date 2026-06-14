# Deploy Enterprise RAG for free (Vercel + Render + Neon + Groq)

This puts the app online for **$0** with **automatic deploys on every `git push`**:

| Part | Host | Free tier |
|---|---|---|
| Frontend (Vite + React) | **Vercel** | Hobby (free, always on) |
| Backend (FastAPI) | **Render** | Free Web Service (sleeps after ~15 min idle) |
| Database (Postgres) | **Neon** | Free serverless Postgres |
| LLM (real answers) | **Groq** | Free OpenAI-compatible API |

You only do these steps **once**. After that, pushing to `main` redeploys both halves
automatically.

> The repo already contains `render.yaml` (backend blueprint) and a Vite frontend that
> Vercel auto-detects. You just connect the accounts.

What runs on the free tier — **LITE_MODE** (set in `render.yaml`):
- in-memory **vector store**, **knowledge graph** and **object storage** (so vectors / files reset on cold-start; **Postgres chunks persist**, so BM25 search keeps working — just re-upload files after a long idle period)
- **null OCR** (text-based PDFs work; scanned PDFs need the full Docker stack)
- **null cross-encoder reranker** (RRF fusion of dense + BM25 still ranks results)
- **inline ingestion** (no Celery worker; runs in-process on each upload)
- **fake embeddings** (deterministic; BM25 + Postgres FTS carries retrieval quality) — see "Real semantic embeddings" at the bottom for the upgrade path.

---

## Step 1 — Database: Neon (free Postgres)

1. Go to **https://neon.tech** → sign up (Continue with GitHub).
2. **New Project** → any name (e.g. `enterprise-rag`). A database is created automatically.
3. On the dashboard, copy the **pooled** connection string. It looks like:
   ```
   postgresql://USER:PASSWORD@ep-xxx-pooler.REGION.aws.neon.tech/neondb?sslmode=require
   ```
4. **Keep it as-is.** The app converts the scheme to `postgresql+asyncpg://` and strips
   the libpq `sslmode=…` for you, then enables SSL on the asyncpg side. Save it for Step 2.

---

## Step 2 — Backend: Render (FastAPI)

1. Go to **https://render.com** → sign up with GitHub.
2. **New → Blueprint** → select this repo `ahammadsk-000/Enterprise_RAG_Platfom`.
   Render reads `render.yaml` and proposes a service named **`enterprise-rag-backend`**.
3. When prompted for env vars marked "set manually":
   - `DATABASE_URL` = the Neon string from Step 1.
   - `CORS_ORIGINS` = `https://localhost` for now (you'll update it in Step 4). Plain URL, comma-separated list, or a JSON array are all accepted.
   - `LLM_API_KEY` = your Groq key (see Step 5; or leave blank now and add it after).
4. Click **Apply**. The first build takes a few minutes. When it's live you'll get:
   ```
   https://enterprise-rag-backend.onrender.com
   ```
5. Verify:
   - `…/api/v1/healthz` → `{"status":"ok",...}`
   - `…/docs` → interactive Swagger API.
   - Free plan sleeps after ~15 min idle; the first request after a nap takes ~30–60s (cold start).

---

## Step 3 — Frontend: Vercel (Vite + React)

1. Go to **https://vercel.com** → sign up with GitHub → **Add New → Project** → import the repo.
2. In the import screen set:
   - **Root Directory** = `frontend`   ← important (the Vite app lives there).
   - Framework Preset = **Vite** (auto-detected).
3. Add an **Environment Variable**:
   - `VITE_API_BASE` = `https://enterprise-rag-backend.onrender.com` (your Render URL, no trailing slash).
4. Click **Deploy**. You'll get a URL like `https://enterprise-rag-platfom.vercel.app`.

The frontend uses `VITE_API_BASE` to call the backend directly (REST + WebSocket).
No proxy needed in production.

---

## Step 4 — Connect them (CORS)

1. Back in **Render → enterprise-rag-backend → Environment**, set:
   - `CORS_ORIGINS` = `https://<your-app>.vercel.app` (your real Vercel URL — no trailing slash).
2. **Save** — Render redeploys (~1 min).
3. Open the Vercel URL, **Register**, upload a `.txt`/`.md`/`.pdf`, and chat. You're live.

---

## Step 5 — Free real AI with Groq (LLM_API_KEY)

The deploy uses **Groq** for the chat LLM (OpenAI-compatible, free tier, fast).

1. Go to **https://console.groq.com** → sign up.
2. **API Keys → Create Key** → copy it.
3. In Render → enterprise-rag-backend → Environment, set:
   - `LLM_API_KEY` = the Groq key.
4. Save (Render redeploys). Chat answers and the **AI inline completion** in the editor
   are now real (powered by `llama-3.3-70b-versatile`).

If you skip this step the app still runs, but the chat will time out on Groq calls.
Alternatively swap `LLM_PROVIDER=fake` (deterministic stub answers) to keep it $0 + offline.

---

## Real semantic embeddings (optional upgrade)

The deploy ships with **fake (deterministic) embeddings** because real
`sentence-transformers` pulls ~600MB of torch — too heavy for Render free. BM25 +
Postgres FTS handles retrieval well, but dense search is synthetic.

To get real semantic dense search on the free tier, point at an OpenAI-compatible
embeddings host (e.g. **Voyage AI**, **Mistral La Plateforme**, **Jina AI** — all
have free tiers):

```
LLM_EMBEDDING_PROVIDER = openai
LLM_EMBEDDING_MODEL    = <provider's embedding model id>
LLM_EMBEDDING_DIM      = <model dim, e.g. 1024>
# These piggyback on the chat LLM_BASE_URL/API_KEY — easiest: use a provider that
# offers both chat + embeddings under one OpenAI-compatible endpoint (Mistral does).
```

For the full real experience (Qdrant, Neo4j, MinIO, Tesseract OCR, cross-encoder
reranker, real Ollama models) use the `enterprise_rag.bat` Docker stack locally,
or upgrade Render → Starter plan + paid Qdrant/Neo4j hosting.

---

## Auto-deploy on push

Both services watch `main`:
- **Render** rebuilds the backend on every push (see `render.yaml: autoDeploy: true`).
- **Vercel** rebuilds the frontend on every push (default).

So future changes are just: `git push origin main` → app updates in ~1–3 min.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Frontend loads but every API call returns CORS error | `CORS_ORIGINS` doesn't include your exact Vercel URL | Set `CORS_ORIGINS=["https://<your-app>.vercel.app"]` (no slash, exact case) and redeploy |
| Login works but Chat says it can't connect | WebSocket blocked or wrong `VITE_API_BASE` | Confirm `VITE_API_BASE` is the Render HTTPS URL; redeploy the frontend |
| First request takes ~45s | Free Render dyno waking from sleep | Normal. Subsequent requests are fast for ~15 min |
| Build fails on Render with "sqlalchemy connect ssl" error | Wrong DSN | Make sure `DATABASE_URL` is the Neon pooled string (with `?sslmode=require`); the app handles the rest |
| Chat returns "I couldn't find anything relevant…" | Vectors lost on dyno restart; only BM25 fired | Upload your docs again (Postgres has the rows but the in-memory vector store reset). After re-upload everything works. |
| `relation "documents" does not exist` | Migrations didn't run | Re-deploy; the start command runs `alembic upgrade head` before `uvicorn`. If it keeps failing, check the Render logs |
