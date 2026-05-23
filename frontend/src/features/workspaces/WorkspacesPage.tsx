import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, ErrorText, Input, Label, Select } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

const STRATEGIES = ["recursive", "parent_child", "semantic", "table_aware", "code_aware"];

export function WorkspacesPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategy, setStrategy] = useState("recursive");
  const [error, setError] = useState<string | null>(null);

  const workspaces = useQuery({ queryKey: ["workspaces"], queryFn: () => api.listWorkspaces() });

  const create = useMutation({
    mutationFn: () => api.createWorkspace({ name, description, chunking_strategy: strategy }),
    onSuccess: () => {
      setName("");
      setDescription("");
      qc.invalidateQueries({ queryKey: ["workspaces"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Failed to create"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteWorkspace(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Workspaces</h1>
        <p className="text-sm text-slate-400">Group documents and conversations; pick a default chunking strategy.</p>
      </header>

      <Card>
        <h2 className="mb-3 text-sm font-medium text-slate-200">Create workspace</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Legal docs" />
          </div>
          <div>
            <Label>Chunking strategy</Label>
            <Select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="w-full">
              {STRATEGIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </div>
        </div>
        <div className="mt-4">
          <Label>Description</Label>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button loading={create.isPending} disabled={name.length < 2} onClick={() => create.mutate()}>
            Create
          </Button>
          <ErrorText>{error}</ErrorText>
        </div>
      </Card>

      <div className="space-y-3">
        {workspaces.data?.map((w) => (
          <Card key={w.id}>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-slate-100">{w.name}</div>
                <div className="text-xs text-slate-500">
                  {w.slug} · <Badge>{w.chunking_strategy}</Badge>
                </div>
                {w.description && <p className="mt-1 text-sm text-slate-400">{w.description}</p>}
              </div>
              <button onClick={() => remove.mutate(w.id)} className="text-xs text-red-400 hover:text-red-300">
                Delete
              </button>
            </div>
          </Card>
        ))}
        {workspaces.data && workspaces.data.length === 0 && (
          <p className="text-sm text-slate-500">No workspaces yet.</p>
        )}
      </div>
    </div>
  );
}
