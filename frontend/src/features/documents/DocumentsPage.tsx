import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Badge, Button, Card, ErrorText } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useWorkspaceStore } from "@/stores/workspace";
import type { DocumentList } from "@/types/api";

const PROCESSING = new Set(["uploaded", "parsing", "parsed", "chunking", "chunked", "embedding"]);

export function DocumentsPage() {
  const qc = useQueryClient();
  const workspaceId = useWorkspaceStore((s) => s.activeId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(),
    refetchInterval: (q) => {
      const data = q.state.data as DocumentList | undefined;
      return data?.items.some((d) => PROCESSING.has(d.status)) ? 4000 : false;
    },
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadDocument(file, workspaceId ?? undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Upload failed"),
  });

  const reindex = useMutation({
    mutationFn: (id: string) => api.reindexDocument(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    const file = e.target.files?.[0];
    if (file) upload.mutate(file);
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Documents</h1>
          <p className="text-sm text-slate-400">Upload files to ingest, chunk, embed and index them.</p>
        </div>
        <div>
          <input ref={fileRef} type="file" className="hidden" onChange={onPick} />
          <Button loading={upload.isPending} onClick={() => fileRef.current?.click()}>
            Upload document
          </Button>
        </div>
      </header>

      <ErrorText>{error}</ErrorText>

      <Card className="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="px-5 py-3">Title</th>
              <th className="px-5 py-3">Type</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Pages</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.data?.items.map((doc) => (
              <tr key={doc.id} className="border-b border-slate-800/60 last:border-0">
                <td className="px-5 py-3 text-slate-100">{doc.title}</td>
                <td className="px-5 py-3 text-slate-400">{doc.mime_type}</td>
                <td className="px-5 py-3">
                  <Badge tone={doc.status}>{doc.status}</Badge>
                  {doc.error && <span className="ml-2 text-xs text-red-400">{doc.error}</span>}
                </td>
                <td className="px-5 py-3 text-slate-400">{doc.page_count ?? "—"}</td>
                <td className="px-5 py-3 text-right">
                  <button
                    onClick={() => reindex.mutate(doc.id)}
                    className="mr-3 text-xs text-brand-400 hover:text-brand-500"
                  >
                    Reindex
                  </button>
                  <button
                    onClick={() => remove.mutate(doc.id)}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {documents.data && documents.data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-10 text-center text-slate-500">
                  No documents yet. Upload one to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
