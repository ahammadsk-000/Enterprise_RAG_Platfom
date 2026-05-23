import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, ErrorText, Input } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useWorkspaceStore } from "@/stores/workspace";

const ROLE_ICON: Record<string, string> = {
  planner: "🧭",
  retriever: "🔎",
  researcher: "📚",
  summarizer: "✍️",
  verifier: "✅",
  citation: "🔗",
};

export function AgentsPage() {
  const [query, setQuery] = useState("");
  const workspaceId = useWorkspaceStore((s) => s.activeId);

  const run = useMutation({
    mutationFn: () => api.agentResearch({ query, top_k: 6, workspace_id: workspaceId ?? undefined }),
  });

  const result = run.data;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Research Agent</h1>
        <p className="text-sm text-slate-400">
          Multi-agent workflow: planner → retriever → summarizer → verifier → citation.
        </p>
      </header>

      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (query.trim()) run.mutate();
          }}
          className="flex gap-2"
        >
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask a research question…" />
          <Button type="submit" loading={run.isPending}>
            Run
          </Button>
        </form>
      </Card>

      {run.error && <ErrorText>{(run.error as ApiError).message}</ErrorText>}

      {result && (
        <div className="space-y-4">
          <Card>
            <div className="mb-2 flex flex-wrap items-center gap-3 text-xs text-slate-400">
              <Badge tone={result.verified ? "indexed" : "failed"}>
                {result.verified ? "verified" : "unverified"}
              </Badge>
              <span>confidence {(result.confidence * 100).toFixed(0)}%</span>
              <span>· {result.total_tokens} tokens</span>
            </div>
            <p className="whitespace-pre-wrap text-sm text-slate-100">{result.answer}</p>
            {result.citations.length > 0 && (
              <div className="mt-3 space-y-2 border-t border-slate-800 pt-3">
                {result.citations.map((c) => (
                  <div key={`${c.marker}-${c.chunk_id}`} className="rounded-md bg-slate-800/50 p-2 text-xs text-slate-300">
                    <span className="mr-2 rounded bg-brand-600 px-1.5 py-0.5 text-white">[{c.marker}]</span>
                    {c.snippet}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {result.sub_questions.length > 0 && (
            <Card>
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Plan</div>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
                {result.sub_questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            </Card>
          )}

          <Card>
            <div className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">Agent timeline</div>
            <ol className="relative space-y-4 border-l border-slate-700 pl-6">
              {result.steps.map((s, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[31px] flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 text-xs">
                    {ROLE_ICON[s.role] ?? "•"}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium capitalize text-slate-100">{s.role}</span>
                    <span className="text-xs text-slate-500">{s.node} · {s.latency_ms} ms</span>
                  </div>
                  <pre className="mt-1 overflow-x-auto rounded bg-slate-800/50 p-2 text-xs text-slate-400">
                    {JSON.stringify(s.output, null, 0)}
                  </pre>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      )}
    </div>
  );
}
