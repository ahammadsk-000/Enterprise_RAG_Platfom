import CodeMirror from "@uiw/react-codemirror";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button, ErrorText, Spinner } from "@/components/ui";
import { aiCompletion } from "@/lib/aiComplete";
import { ApiError, api, downloadDocumentFile } from "@/lib/api";
import { editorExtensions } from "@/lib/editor";

interface Props {
  documentId: string;
  onClose: () => void;
  onSaved: () => void;
}

export function DocumentEditor({ documentId, onClose, onSaved }: Props) {
  const [value, setValue] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiEnabled, setAiEnabled] = useState(false);

  const content = useQuery({
    queryKey: ["doc-content", documentId],
    queryFn: () => api.getDocumentContent(documentId),
  });

  useEffect(() => {
    if (content.data?.content != null) setValue(content.data.content);
  }, [content.data]);

  const doc = content.data;
  const extensions = doc
    ? [
        ...editorExtensions(doc.title, doc.mime_type),
        ...(aiEnabled ? aiCompletion((prefix) => api.assistComplete(prefix).then((r) => r.completion)) : []),
      ]
    : [];

  async function save() {
    setError(null);
    setSaving(true);
    try {
      await api.saveDocumentContent(documentId, value);
      setDirty(false);
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function downloadEdited() {
    const blob = new Blob([value], { type: doc?.mime_type ?? "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = doc?.title ?? "document.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="flex h-[85vh] w-full max-w-4xl flex-col rounded-xl border border-slate-700 bg-slate-900 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <div className="truncate">
            <div className="truncate font-medium text-slate-100">{doc?.title ?? "Loading…"}</div>
            <div className="text-xs text-slate-500">
              {doc?.mime_type}
              {dirty && <span className="ml-2 text-amber-400">• unsaved changes</span>}
            </div>
          </div>
          <div className="flex items-center gap-4">
            {doc?.editable && (
              <label className="flex items-center gap-2 text-xs text-slate-300" title="LLM ghost-text suggestions; Tab to accept (real on full stack, stubbed in demo)">
                <input type="checkbox" checked={aiEnabled} onChange={(e) => setAiEnabled(e.target.checked)} />
                AI autocomplete (Tab)
              </label>
            )}
            <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
              ✕
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {content.isLoading && (
            <div className="flex h-full items-center justify-center text-slate-400">
              <Spinner />
            </div>
          )}
          {doc && !doc.editable && (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center text-slate-400">
              <p>
                <span className="text-slate-200">{doc.mime_type}</span> files can't be edited as text.
              </p>
              <Button variant="ghost" onClick={() => downloadDocumentFile(documentId, doc.title)}>
                Download original
              </Button>
            </div>
          )}
          {doc?.editable && (
            <CodeMirror
              value={value}
              height="100%"
              theme="dark"
              extensions={extensions}
              onChange={(v) => {
                setValue(v);
                setDirty(true);
              }}
              style={{ height: "100%", fontSize: 14 }}
            />
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-slate-800 px-5 py-3">
          <ErrorText>{error}</ErrorText>
          <div className="ml-auto flex gap-2">
            {doc?.editable && (
              <Button variant="ghost" onClick={downloadEdited}>
                Download
              </Button>
            )}
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
            {doc?.editable && (
              <Button loading={saving} disabled={!dirty} onClick={save}>
                Save &amp; re-index
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
