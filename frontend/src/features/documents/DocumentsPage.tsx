import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Suspense, lazy, useRef, useState } from "react";

import { Badge, Button, Card, ErrorText } from "@/components/ui";
import { ApiError, api, downloadDocumentFile } from "@/lib/api";
import { useWorkspaceStore } from "@/stores/workspace";
import type { DocumentList } from "@/types/api";

// Lazy-loaded so CodeMirror is only fetched when the editor opens.
const DocumentEditor = lazy(() =>
  import("@/features/documents/DocumentEditor").then((m) => ({ default: m.DocumentEditor })),
);

const PROCESSING = new Set(["uploaded", "parsing", "parsed", "chunking", "chunked", "embedding"]);
const EDITABLE_MIME = new Set(["application/json", "application/xml", "application/csv", "application/x-yaml"]);

// Mirrors the backend rule: text-based files are editable in place.
const isTextEditable = (mime: string) => mime.startsWith("text/") || EDITABLE_MIME.has(mime);

export function DocumentsPage() {
  const qc = useQueryClient();
  const workspaceId = useWorkspaceStore((s) => s.activeId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

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
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      setNotice(
        res.duplicate
          ? `"${res.document.title}" is already indexed — duplicate skipped (same content).`
          : `"${res.document.title}" uploaded — ingesting…`,
      );
    },
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

  const extract = useMutation({
    mutationFn: (id: string) => api.extractMarkdown(id),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      setNotice(
        res.duplicate
          ? `Already extracted — opening "${res.document.title}".`
          : `Extracted text → "${res.document.title}" (editable, indexing). Original kept.`,
      );
      setEditingId(res.document.id); // open the new editable markdown doc
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Extract failed"),
  });

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    setNotice(null);
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
      {notice && <p className="text-sm text-brand-400">{notice}</p>}

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
                <td className="space-x-3 px-5 py-3 text-right text-xs">
                  {isTextEditable(doc.mime_type) ? (
                    <button onClick={() => setEditingId(doc.id)} className="text-slate-300 hover:text-white">
                      Edit
                    </button>
                  ) : (
                    <button
                      onClick={() => extract.mutate(doc.id)}
                      className="text-slate-300 hover:text-white"
                      title="Extract the text into an editable Markdown document"
                    >
                      Extract → MD
                    </button>
                  )}
                  <button
                    onClick={() => downloadDocumentFile(doc.id, doc.title)}
                    className="text-slate-300 hover:text-white"
                  >
                    Download
                  </button>
                  <button
                    onClick={() => reindex.mutate(doc.id)}
                    className="text-brand-400 hover:text-brand-500"
                  >
                    Reindex
                  </button>
                  <button
                    onClick={() => remove.mutate(doc.id)}
                    className="text-red-400 hover:text-red-300"
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

      {editingId && (
        <Suspense fallback={null}>
          <DocumentEditor
            documentId={editingId}
            onClose={() => setEditingId(null)}
            onSaved={() => {
              qc.invalidateQueries({ queryKey: ["documents"] });
              setNotice("Saved — re-indexing the updated document…");
            }}
          />
        </Suspense>
      )}
    </div>
  );
}
