import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, ErrorText, Input, Label, Textarea } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { EvalRunResult } from "@/types/api";

interface DraftSample {
  question: string;
  ground_truth: string;
  contexts: string; // newline-separated
}

const EMPTY: DraftSample = { question: "", ground_truth: "", contexts: "" };

export function EvaluationPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [samples, setSamples] = useState<DraftSample[]>([{ ...EMPTY }]);
  const [error, setError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<EvalRunResult | null>(null);

  const datasets = useQuery({ queryKey: ["eval-datasets"], queryFn: () => api.listDatasets() });

  const create = useMutation({
    mutationFn: () =>
      api.createDataset({
        name,
        samples: samples
          .filter((s) => s.question.trim())
          .map((s) => ({
            question: s.question,
            ground_truth: s.ground_truth || null,
            contexts: s.contexts.split("\n").map((c) => c.trim()).filter(Boolean),
          })),
      }),
    onSuccess: () => {
      setName("");
      setSamples([{ ...EMPTY }]);
      qc.invalidateQueries({ queryKey: ["eval-datasets"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Failed to create dataset"),
  });

  const run = useMutation({
    mutationFn: (id: string) => api.runEvaluation(id),
    onSuccess: (res) => setLastRun(res),
  });

  function patch(i: number, field: keyof DraftSample, value: string) {
    setSamples((prev) => prev.map((s, idx) => (idx === i ? { ...s, [field]: value } : s)));
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Evaluation</h1>
        <p className="text-sm text-slate-400">
          Score answers on faithfulness, relevancy, context precision/recall, and hallucination.
        </p>
      </header>

      <Card>
        <h2 className="mb-3 text-sm font-medium text-slate-200">Create golden dataset</h2>
        <Label>Dataset name</Label>
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="QA smoke set" />

        <div className="mt-4 space-y-4">
          {samples.map((s, i) => (
            <div key={i} className="rounded-md border border-slate-800 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs text-slate-500">Sample {i + 1}</span>
                {samples.length > 1 && (
                  <button
                    className="text-xs text-red-400 hover:text-red-300"
                    onClick={() => setSamples((p) => p.filter((_, idx) => idx !== i))}
                  >
                    Remove
                  </button>
                )}
              </div>
              <Input
                value={s.question}
                onChange={(e) => patch(i, "question", e.target.value)}
                placeholder="Question"
                className="mb-2"
              />
              <Input
                value={s.ground_truth}
                onChange={(e) => patch(i, "ground_truth", e.target.value)}
                placeholder="Ground truth (optional)"
                className="mb-2"
              />
              <Textarea
                value={s.contexts}
                onChange={(e) => patch(i, "contexts", e.target.value)}
                placeholder="Context passages — one per line"
                rows={3}
              />
            </div>
          ))}
        </div>

        <div className="mt-3 flex items-center gap-3">
          <Button variant="ghost" onClick={() => setSamples((p) => [...p, { ...EMPTY }])}>
            + Add sample
          </Button>
          <Button loading={create.isPending} disabled={!name || !samples.some((s) => s.question)} onClick={() => create.mutate()}>
            Create dataset
          </Button>
          <ErrorText>{error}</ErrorText>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-medium text-slate-200">Datasets</h2>
        <div className="space-y-2">
          {datasets.data?.map((d) => (
            <div key={d.id} className="flex items-center justify-between rounded-md bg-slate-800/40 px-3 py-2 text-sm">
              <span className="text-slate-100">{d.name}</span>
              <Button variant="ghost" loading={run.isPending} onClick={() => run.mutate(d.id)}>
                Run eval
              </Button>
            </div>
          ))}
          {datasets.data && datasets.data.length === 0 && <p className="text-sm text-slate-500">No datasets yet.</p>}
        </div>
      </Card>

      {lastRun && (
        <Card>
          <h2 className="mb-3 text-sm font-medium text-slate-200">
            Results · {lastRun.sample_count} samples
          </h2>
          <div className="mb-4 flex flex-wrap gap-2">
            {Object.entries(lastRun.metrics).map(([k, v]) => (
              <Badge key={k}>
                {k}: {v.toFixed(3)}
              </Badge>
            ))}
          </div>
          <div className="space-y-2">
            {lastRun.results.map((r) => (
              <div key={r.sample_id} className="rounded-md bg-slate-800/40 p-3 text-xs">
                <div className="text-slate-300">Q: {r.question}</div>
                <div className="mt-1 text-slate-400">A: {r.answer}</div>
                <div className="mt-1 flex flex-wrap gap-2 text-slate-500">
                  {Object.entries(r.scores).map(([k, v]) => (
                    <span key={k}>
                      {k} {v.toFixed(2)}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
