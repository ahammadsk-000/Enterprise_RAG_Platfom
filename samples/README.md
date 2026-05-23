# Sample documents

Ready-made files to exercise the platform with richer content than a one-liner. They
are intentionally multi-section so you can see real **chunking**, **ranking**, **graph
relations**, and **citations**. (Demo mode supports `.txt` / `.md` / `.html`; the full
stack also handles PDF/DOCX.)

| File | Format | Good for |
|------|--------|----------|
| `acme_company_handbook.md` | Markdown (+ table) | org facts, people, departments, history |
| `sentinelguard_product_faq.txt` | Plain text | product Q&A (SLA, pricing, integrations) |
| `acme_security_policy.md` | Markdown | policy lookups (access control, incidents) |
| `incident_postmortem_2024.html` | HTML | tests the HTML parser; root-cause questions |
| `rag_platform_overview.txt` | Plain text | technical questions about RAG itself |

The Acme files share entities (Jane Doe, Raj Patel, SentinelGuard, DataShield, Austin…)
so the **knowledge graph connects across documents**.

## How to load
1. **Workspaces** → create one (e.g. `Acme`) and select it in the switcher.
2. **Documents** → upload all five files; wait until each shows `indexed`.
3. Now try the queries below.

## Suggested queries per feature

**Search** (try Hybrid, then toggle Re-rank / strategy)
- `what is the uptime SLA` → SentinelGuard FAQ chunk on the 99.9% SLA
- `who did Acme acquire` → handbook history + FAQ mentions of DataShield
- `how is access controlled` → security policy RBAC/MFA chunk
- `what caused the outage` → post-mortem root-cause chunk

**Chat** (streaming, grounded + citations)
- `Where is Acme headquartered and when did it move there?`
- `What does SentinelGuard cost and what does Enterprise add?`
- `Summarize the July 2024 incident and its action items.`

**Graph** (entity traversal, hops = 2)
- `Acme` → Jane Doe, Raj Patel, SentinelGuard, DataShield, Austin, Boston…
- `DataShield` → Acme, Tom Becker, Seattle
- `Raj Patel` → Acme, CTO-related entities

**Agents** (multi-step research)
- `Who founded Acme, what do they build, and what did they acquire?`
- `What are Acme's security and compliance commitments?`

**Evaluation** (build a golden set)
- Q: `What is the SentinelGuard uptime SLA?` · ground truth: `99.9%`
  · context: paste the SLA paragraph from the FAQ.
- Q: `Who is Acme's CTO?` · ground truth: `Raj Patel`
  · context: paste the "About Acme" paragraph from the handbook.

**Admin** — after the above, open it to see documents/messages/tokens/retrieval counts.

> Reminder: in demo mode the LLM text is a deterministic stub, so Chat/Agents prose is
> placeholder — but retrieval, citations, confidence, graph, and eval metrics are all
> real. Run the full-stack launcher (Ollama) for real generated answers.
