"""End-to-end probe against the live Render+Vercel deploy.

Run as: python scripts/e2e_probe.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "https://enterprise-rag-backend-2250.onrender.com/api/v1"
PASS: list[str] = []
FAIL: list[tuple[str, str]] = []


def ok(name: str, detail: str = "") -> None:
    PASS.append(name)
    suffix = f" — {detail}" if detail else ""
    print(f"  PASS  {name}{suffix}")


def bad(name: str, detail: str) -> None:
    FAIL.append((name, detail))
    print(f"  FAIL  {name} — {detail}")


def req(method, path, *, token=None, body=None, raw_body=None, headers=None, timeout=180):
    h = dict(headers or {})
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    elif raw_body is not None:
        data = raw_body
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read()) if resp.status != 204 else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]


# ── 1. health ──────────────────────────────────────────────────────────────
print("\n[1] HEALTH")
s, b = req("GET", "/healthz")
ok("healthz", f"status={s}") if s == 200 else bad("healthz", f"{s} {b}")

# ── 2. auth ────────────────────────────────────────────────────────────────
print("\n[2] AUTH")
sfx = str(int(time.time()))
email = f"e2e{sfx}@example.com"
s, reg = req(
    "POST",
    "/auth/register",
    body={
        "email": email,
        "password": "E2eTest1234!",
        "full_name": "E2E User",
        "organization_name": f"E2EOrg{sfx}",
    },
)
if s == 201:
    tok = reg["access_token"]
    ok("register", "org+user created")
else:
    bad("register", f"{s} {reg}")
    sys.exit()

s, login = req("POST", "/auth/login", body={"email": email, "password": "E2eTest1234!"})
ok("login", "tokens issued") if s == 200 else bad("login", f"{s} {login}")

s, me = req("GET", "/auth/me", token=tok)
ok("me", f"user={me['user']['email']} role={me.get('role')}") if s == 200 else bad("me", f"{s} {me}")

# ── 3. upload ──────────────────────────────────────────────────────────────
print("\n[3] DOCUMENT UPLOAD + INGESTION")
txt = (
    b"Enterprise RAG Platform overview.\n"
    b"The platform supports hybrid retrieval combining BM25 and dense vectors.\n"
    b"It uses PostgreSQL for metadata, Qdrant for vectors, and Neo4j for graph relations.\n"
    b"Fast and accurate document search is the primary goal.\n"
    b"The system is built with FastAPI on the backend and React on the frontend.\n"
)
bnd = f"----e2e{sfx}"
body = (
    f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; "
    f"filename=\"rag-overview.txt\"\r\nContent-Type: text/plain\r\n\r\n"
).encode() + txt + f"\r\n--{bnd}--\r\n".encode()
s, up = req(
    "POST",
    "/documents",
    token=tok,
    raw_body=body,
    headers={"Content-Type": f"multipart/form-data; boundary={bnd}"},
)
if s == 201:
    doc_id = up["document"]["id"]
    ok("upload", f"id={doc_id[:8]}.. dup={up['duplicate']}")
else:
    bad("upload", f"{s} {up}")
    sys.exit()

final, last_err, cur = None, None, None
for _ in range(20):
    time.sleep(2)
    s, d = req("GET", "/documents?limit=5", token=tok)
    if s != 200:
        continue
    cur = next((x for x in d["items"] if x["id"] == doc_id), None)
    if not cur:
        continue
    final = cur["status"]
    last_err = cur.get("error")
    if final in ("indexed", "failed", "parsed"):
        break
(
    ok(f"ingestion -> {final}", f"pages={cur.get('page_count') if cur else None}")
    if final == "indexed"
    else bad(f"ingestion -> {final}", f"error={last_err!r}")
)

s, ds = req("GET", f"/documents/{doc_id}/status", token=tok)
if s == 200:
    jobs = " ".join(j["stage"] + "=" + j["status"] for j in ds["jobs"])
    ok("document status", f"chunks={ds['chunk_count']} jobs=[{jobs}]")
else:
    bad("document status", f"{s} {ds}")

# ── 4. workspaces ──────────────────────────────────────────────────────────
print("\n[4] WORKSPACES")
s, ws = req("POST", "/workspaces", token=tok, body={"name": "E2E WS", "description": "probe"})
ws_id = ws["id"] if s == 201 else None
ok("create workspace", f"id={ws_id[:8]}..") if ws_id else bad("create workspace", f"{s} {ws}")

s, lst = req("GET", "/workspaces", token=tok)
ok("list workspaces", f"count={len(lst)}") if s == 200 else bad("list workspaces", f"{s} {lst}")

# ── 5. search ──────────────────────────────────────────────────────────────
print("\n[5] SEARCH")
for strategy in ("hybrid", "dense", "bm25"):
    s, r = req(
        "POST",
        "/search",
        token=tok,
        body={"query": "hybrid retrieval BM25", "top_k": 3, "strategy": strategy, "rerank": False},
    )
    if s == 200:
        ok(f"search [{strategy}]", f"hits={len(r['hits'])} latency={r.get('latency_ms', 0):.0f}ms")
    else:
        bad(f"search [{strategy}]", f"{s} {r}")

# ── 6. rag query ───────────────────────────────────────────────────────────
print("\n[6] RAG QUERY (real LLM via Groq)")
s, rag = req(
    "POST",
    "/rag/query",
    token=tok,
    body={
        "query": "What backend framework does the platform use?",
        "top_k": 3,
        "strategy": "hybrid",
        "rerank": False,
    },
    timeout=120,
)
if s == 200:
    ans = rag.get("answer", "")[:150].replace("\n", " ")
    ok("rag query", f"answer={ans!r}... citations={len(rag.get('citations', []))}")
else:
    bad("rag query", f"{s} {rag}")

# ── 7. chat ────────────────────────────────────────────────────────────────
print("\n[7] CHAT CONVERSATION")
s, conv = req("POST", "/chat/conversations", token=tok, body={"title": "E2E chat"})
conv_id = conv["id"] if s in (200, 201) else None
ok("create conversation", f"id={conv_id[:8]}..") if conv_id else bad("create conversation", f"{s} {conv}")

s, conv_list = req("GET", "/chat/conversations", token=tok)
(
    ok("list conversations", f"count={len(conv_list)}")
    if s == 200
    else bad("list conversations", f"{s} {conv_list}")
)

s, msgs = req("GET", f"/chat/conversations/{conv_id}/messages", token=tok)
ok("list messages", f"count={len(msgs)}") if s == 200 else bad("list messages", f"{s} {msgs}")

s, _ = req("PATCH", f"/chat/conversations/{conv_id}", token=tok, body={"title": "E2E renamed"})
ok("rename conversation") if s == 200 else bad("rename conversation", f"{s}")

# ── 8. graph ───────────────────────────────────────────────────────────────
print("\n[8] GRAPH")
s, g = req("POST", "/graph/explore", token=tok, body={"query": "platform", "hops": 1, "limit": 10})
(
    ok("graph explore", f"seeds={len(g.get('seeds', []))} neighbors={len(g.get('neighbors', []))}")
    if s == 200
    else bad("graph explore", f"{s} {g}")
)

# ── 9. agents ──────────────────────────────────────────────────────────────
print("\n[9] AGENTS (research)")
s, ar = req(
    "POST",
    "/agents/research",
    token=tok,
    body={"query": "platform overview", "top_k": 3},
    timeout=180,
)
if s == 200:
    ok("agent research", f"sources={len(ar.get('sources', []))} answer_chars={len(ar.get('answer', ''))}")
else:
    bad("agent research", f"{s} {ar}")

# ── 10. evaluation ─────────────────────────────────────────────────────────
print("\n[10] EVALUATION")
s, dsl = req("GET", "/evaluation/datasets", token=tok)
ok("list datasets", f"count={len(dsl)}") if s == 200 else bad("list datasets", f"{s} {dsl}")

# ── 11. admin analytics ────────────────────────────────────────────────────
print("\n[11] ADMIN")
s, a = req("GET", "/admin/analytics/overview", token=tok)
(
    ok("analytics", f"docs={a.get('documents_total')} chunks={a.get('chunks_total')}")
    if s == 200
    else bad("analytics", f"{s} {a}")
)

# ── 12. cleanup ────────────────────────────────────────────────────────────
print("\n[12] CLEANUP")
s, _ = req("DELETE", f"/chat/conversations/{conv_id}", token=tok)
ok("delete conversation") if s == 204 else bad("delete conversation", f"{s}")
s, _ = req("DELETE", f"/workspaces/{ws_id}", token=tok)
ok("delete workspace") if s == 204 else bad("delete workspace", f"{s}")
s, _ = req("DELETE", f"/documents/{doc_id}", token=tok)
ok("delete document") if s == 204 else bad("delete document", f"{s}")

# ── summary ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"SUMMARY: {len(PASS)} pass, {len(FAIL)} fail")
if FAIL:
    print("\nFailures:")
    for name, det in FAIL:
        print(f"  - {name}: {det}")
