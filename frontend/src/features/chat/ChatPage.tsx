import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, Input } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { RagAnswer } from "@/types/api";

interface Turn {
  question: string;
  answer?: RagAnswer;
  error?: string;
}

function confidenceTone(c: number): string {
  if (c >= 0.66) return "indexed";
  if (c >= 0.33) return "chunking";
  return "failed";
}

export function ChatPage() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);

  const ask = useMutation({
    mutationFn: (q: string) => api.ragQuery({ query: q, top_k: 6, strategy: "hybrid", rerank: true }),
    onSuccess: (answer, q) =>
      setTurns((prev) => prev.map((t) => (t.question === q && !t.answer ? { ...t, answer } : t))),
    onError: (e, q) =>
      setTurns((prev) =>
        prev.map((t) =>
          t.question === q && !t.answer
            ? { ...t, error: e instanceof ApiError ? e.message : "Request failed" }
            : t,
        ),
      ),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q) return;
    setTurns((prev) => [...prev, { question: q }]);
    ask.mutate(q);
    setInput("");
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-white">Chat</h1>
        <p className="text-sm text-slate-400">Ask questions and get citation-grounded answers from your knowledge base.</p>
      </header>

      <div className="flex-1 space-y-6 overflow-y-auto pr-1">
        {turns.length === 0 && (
          <div className="mt-20 text-center text-slate-500">Ask your first question to get started.</div>
        )}
        {turns.map((turn, i) => (
          <div key={i} className="space-y-3">
            <div className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2 text-sm text-white">
                {turn.question}
              </div>
            </div>

            {turn.error && (
              <Card className="border-red-900 bg-red-950/40 text-sm text-red-300">{turn.error}</Card>
            )}

            {turn.answer && (
              <Card>
                <p className="whitespace-pre-wrap text-sm text-slate-100">{turn.answer.answer}</p>

                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                  <Badge tone={confidenceTone(turn.answer.confidence)}>
                    confidence {(turn.answer.confidence * 100).toFixed(0)}%
                  </Badge>
                  <span>{turn.answer.model}</span>
                  <span>· {turn.answer.retrieved} retrieved</span>
                  <span>· {turn.answer.latency_ms} ms</span>
                  <span>· {turn.answer.prompt_tokens + turn.answer.completion_tokens} tokens</span>
                </div>

                {turn.answer.citations.length > 0 && (
                  <div className="mt-4 space-y-2 border-t border-slate-800 pt-3">
                    <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Sources</div>
                    {turn.answer.citations.map((c) => (
                      <div key={`${c.marker}-${c.chunk_id}`} className="rounded-md bg-slate-800/50 p-3 text-xs">
                        <div className="mb-1 flex items-center gap-2 text-slate-400">
                          <span className="rounded bg-brand-600 px-1.5 py-0.5 text-white">[{c.marker}]</span>
                          {c.page_from != null && <span>page {c.page_from}</span>}
                          <span>· score {c.score.toFixed(3)}</span>
                        </div>
                        <p className="text-slate-300">{c.snippet}</p>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            )}

            {!turn.answer && !turn.error && <div className="text-sm text-slate-500">Thinking…</div>}
          </div>
        ))}
      </div>

      <form onSubmit={submit} className="mt-4 flex gap-2 border-t border-slate-800 pt-4">
        <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question…" />
        <Button type="submit" loading={ask.isPending}>
          Send
        </Button>
      </form>
    </div>
  );
}
