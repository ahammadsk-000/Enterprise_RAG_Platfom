import { useQuery } from "@tanstack/react-query";

import { Card, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import type { AnalyticsOverview } from "@/types/api";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
    </Card>
  );
}

export function AdminPage() {
  const overview = useQuery({ queryKey: ["analytics"], queryFn: () => api.analyticsOverview() });
  const d = overview.data as AnalyticsOverview | undefined;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Admin Analytics</h1>
        <p className="text-sm text-slate-400">Usage across your organization.</p>
      </header>

      {overview.isLoading && (
        <div className="text-slate-400">
          <Spinner />
        </div>
      )}

      {d && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Stat label="Documents" value={`${d.documents_indexed} / ${d.documents_total} indexed`} />
          <Stat label="Conversations" value={d.conversations} />
          <Stat label="Messages" value={d.messages} />
          <Stat label="Total tokens" value={d.total_tokens.toLocaleString()} />
          <Stat label="Avg confidence" value={d.avg_confidence != null ? `${(d.avg_confidence * 100).toFixed(0)}%` : "—"} />
          <Stat label="Retrieval queries" value={d.retrieval_queries} />
          <Stat
            label="Avg retrieval latency"
            value={d.avg_retrieval_latency_ms != null ? `${d.avg_retrieval_latency_ms} ms` : "—"}
          />
          <Stat label="Agent runs" value={d.agent_runs} />
        </div>
      )}
    </div>
  );
}
