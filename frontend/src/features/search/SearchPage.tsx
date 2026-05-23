import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, ErrorText, Input, Label, Select } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { RetrievalStrategy, SearchResponse } from "@/types/api";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [strategy, setStrategy] = useState<RetrievalStrategy>("hybrid");
  const [topK, setTopK] = useState(10);
  const [rerank, setRerank] = useState(true);

  const search = useMutation({
    mutationFn: () => api.search({ query, top_k: topK, strategy, rerank }),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) search.mutate();
  }

  const result = search.data as SearchResponse | undefined;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Search</h1>
        <p className="text-sm text-slate-400">Hybrid dense + keyword retrieval over your indexed documents.</p>
      </header>

      <Card>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label>Query</Label>
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask anything about your docs…" />
          </div>
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <Label>Strategy</Label>
              <Select value={strategy} onChange={(e) => setStrategy(e.target.value as RetrievalStrategy)}>
                <option value="hybrid">Hybrid</option>
                <option value="dense">Dense</option>
                <option value="bm25">BM25</option>
              </Select>
            </div>
            <div>
              <Label>Top K</Label>
              <Input
                type="number"
                min={1}
                max={50}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-24"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={rerank} onChange={(e) => setRerank(e.target.checked)} />
              Re-rank
            </label>
            <Button type="submit" loading={search.isPending}>
              Search
            </Button>
          </div>
        </form>
      </Card>

      {search.error && <ErrorText>{(search.error as ApiError).message}</ErrorText>}

      {result && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            {result.hits.length} results · {result.strategy} · {result.latency_ms} ms
          </p>
          {result.hits.map((hit) => (
            <Card key={hit.chunk_id}>
              <div className="mb-2 flex items-center gap-3 text-xs text-slate-400">
                <Badge>{hit.source}</Badge>
                <span>score {hit.score.toFixed(4)}</span>
                {hit.page_from != null && <span>· page {hit.page_from}</span>}
                <span>· {hit.chunk_type}</span>
              </div>
              <p className="text-sm text-slate-200">{hit.content}</p>
            </Card>
          ))}
          {result.hits.length === 0 && <p className="text-sm text-slate-500">No matches found.</p>}
        </div>
      )}
    </div>
  );
}
