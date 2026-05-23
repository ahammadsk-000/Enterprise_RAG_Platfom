import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, ErrorText, Input, Label, Select } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

export function GraphPage() {
  const [query, setQuery] = useState("");
  const [hops, setHops] = useState(2);

  const explore = useMutation({
    mutationFn: () => api.graphExplore({ query, hops, limit: 50 }),
  });

  const result = explore.data;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Knowledge Graph</h1>
        <p className="text-sm text-slate-400">
          Finds entities in your query and traverses their relationships extracted during ingestion.
        </p>
      </header>

      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (query.trim()) explore.mutate();
          }}
          className="flex flex-wrap items-end gap-4"
        >
          <div className="flex-1 min-w-[240px]">
            <Label>Entity / topic</Label>
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. a name or term from your docs" />
          </div>
          <div>
            <Label>Hops</Label>
            <Select value={hops} onChange={(e) => setHops(Number(e.target.value))}>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
            </Select>
          </div>
          <Button type="submit" loading={explore.isPending}>
            Explore
          </Button>
        </form>
      </Card>

      {explore.error && <ErrorText>{(explore.error as ApiError).message}</ErrorText>}

      {result && (
        <div className="space-y-4">
          <Card>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Seed entities</div>
            {result.seeds.length === 0 ? (
              <p className="text-sm text-slate-500">No known entities found in the query.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {result.seeds.map((s) => (
                  <span key={s} className="rounded-full bg-brand-600 px-3 py-1 text-xs text-white">
                    {s}
                  </span>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <div className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
              Related entities ({result.neighbors.length})
            </div>
            <div className="space-y-2">
              {result.neighbors.map((n, i) => (
                <div key={`${n.name}-${i}`} className="flex items-center gap-3 rounded-md bg-slate-800/50 px-3 py-2 text-sm">
                  <span className="text-slate-100">{n.name}</span>
                  <Badge>{n.type}</Badge>
                  <span className="text-xs text-slate-500">
                    {n.direction === "out" ? "→" : "←"} {n.relation}
                  </span>
                </div>
              ))}
              {result.neighbors.length === 0 && (
                <p className="text-sm text-slate-500">No relationships found. Try ingesting more documents.</p>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
