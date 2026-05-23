import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { Badge, Button, Card, Input } from "@/components/ui";
import { api } from "@/lib/api";
import { openChatSocket } from "@/lib/ws";
import { useWorkspaceStore } from "@/stores/workspace";
import type { Citation } from "@/types/api";

interface UIMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number | null;
  streaming?: boolean;
  error?: string;
}

function confidenceTone(c: number): string {
  if (c >= 0.66) return "indexed";
  if (c >= 0.33) return "chunking";
  return "failed";
}

export function ChatPage() {
  const qc = useQueryClient();
  const workspaceId = useWorkspaceStore((s) => s.activeId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const socketRef = useRef<WebSocket | null>(null);
  const socketConvRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const conversations = useQuery({ queryKey: ["conversations"], queryFn: () => api.listConversations() });

  // Load history only when the user explicitly opens an existing conversation
  // (NOT when send() creates one — that would race with and wipe the streaming answer).
  async function selectConversation(id: string) {
    if (streaming) return;
    setSelectedId(id);
    const msgs = await api.listMessages(id);
    setMessages(
      msgs.map((m) => ({
        id: m.id,
        role: m.role === "assistant" ? "assistant" : "user",
        content: m.content,
        citations: m.citations,
        confidence: m.confidence,
      })),
    );
  }

  function newChat() {
    if (streaming) return;
    setSelectedId(null);
    setMessages([]);
  }

  function startRename(id: string, current: string) {
    setRenamingId(id);
    setDraftTitle(current);
  }

  async function saveRename(id: string) {
    const title = draftTitle.trim();
    setRenamingId(null);
    if (!title) return;
    await api.renameConversation(id, title);
    qc.invalidateQueries({ queryKey: ["conversations"] });
  }

  async function deleteConversation(id: string) {
    if (streaming) return;
    await api.deleteConversation(id);
    qc.invalidateQueries({ queryKey: ["conversations"] });
    if (selectedId === id) {
      setSelectedId(null);
      setMessages([]);
    }
  }

  // Close the socket on unmount.
  useEffect(() => () => socketRef.current?.close(), []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function updateLastAssistant(fn: (m: UIMessage) => UIMessage) {
    setMessages((prev) => {
      const idx = [...prev].reverse().findIndex((m) => m.role === "assistant");
      if (idx === -1) return prev;
      const realIdx = prev.length - 1 - idx;
      return prev.map((m, i) => (i === realIdx ? fn(m) : m));
    });
  }

  function ensureSocket(convId: string): WebSocket {
    if (socketRef.current && socketConvRef.current === convId && socketRef.current.readyState <= WebSocket.OPEN) {
      return socketRef.current;
    }
    socketRef.current?.close();
    const sock = openChatSocket(convId, {
      onEvent: (event) => {
        if (event.type === "token") {
          updateLastAssistant((m) => ({ ...m, content: m.content + event.content }));
        } else if (event.type === "done") {
          updateLastAssistant((m) => ({
            ...m,
            citations: event.citations,
            confidence: event.confidence,
            streaming: false,
          }));
          setStreaming(false);
          qc.invalidateQueries({ queryKey: ["conversations"] });
        } else if (event.type === "error") {
          updateLastAssistant((m) => ({ ...m, error: event.detail, streaming: false }));
          setStreaming(false);
        }
      },
      onClose: () => setStreaming(false),
    });
    socketRef.current = sock;
    socketConvRef.current = convId;
    return sock;
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    let convId = selectedId;
    if (!convId) {
      const convo = await api.createConversation({ workspace_id: workspaceId ?? undefined });
      qc.invalidateQueries({ queryKey: ["conversations"] });
      convId = convo.id;
      setSelectedId(convo.id);
    }

    setInput("");
    setStreaming(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "", streaming: true },
    ]);

    const sock = ensureSocket(convId);
    const payload = JSON.stringify({ query: text, top_k: 6, strategy: "hybrid", rerank: true });
    if (sock.readyState === WebSocket.OPEN) sock.send(payload);
    else sock.addEventListener("open", () => sock.send(payload), { once: true });
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-4">
      {/* Conversation sidebar */}
      <div className="flex w-56 flex-col">
        <Button className="mb-3 w-full" onClick={newChat}>
          + New chat
        </Button>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {conversations.data?.map((c) =>
            renamingId === c.id ? (
              <input
                key={c.id}
                autoFocus
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                onBlur={() => void saveRename(c.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void saveRename(c.id);
                  if (e.key === "Escape") setRenamingId(null);
                }}
                className="w-full rounded-md border border-brand-500 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none"
              />
            ) : (
              <div
                key={c.id}
                className={`group flex items-center rounded-md text-sm transition ${
                  selectedId === c.id ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-800/60"
                }`}
              >
                <button
                  onClick={() => void selectConversation(c.id)}
                  className="flex-1 truncate px-3 py-2 text-left"
                >
                  {c.title}
                </button>
                <div className="flex shrink-0 items-center gap-1 pr-2 opacity-0 group-hover:opacity-100">
                  <button
                    title="Rename"
                    onClick={() => startRename(c.id, c.title)}
                    className="rounded p-1 text-slate-400 hover:text-white"
                  >
                    ✏️
                  </button>
                  <button
                    title="Delete"
                    onClick={() => void deleteConversation(c.id)}
                    className="rounded p-1 text-slate-400 hover:text-red-400"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ),
          )}
        </div>
      </div>

      {/* Conversation */}
      <div className="flex flex-1 flex-col">
        <header className="mb-4">
          <h1 className="text-2xl font-semibold text-white">Chat</h1>
          <p className="text-sm text-slate-400">Streaming, citation-grounded answers from your knowledge base.</p>
        </header>

        <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <div className="mt-20 text-center text-slate-500">Ask a question to start the conversation.</div>
          )}
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2 text-sm text-white">
                  {m.content}
                </div>
              </div>
            ) : (
              <Card key={i}>
                {m.error ? (
                  <p className="text-sm text-red-400">{m.error}</p>
                ) : (
                  <p className="whitespace-pre-wrap text-sm text-slate-100">
                    {m.content}
                    {m.streaming && <span className="ml-1 animate-pulse">▋</span>}
                  </p>
                )}
                {!m.streaming && m.confidence != null && (
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    <Badge tone={confidenceTone(m.confidence)}>confidence {(m.confidence * 100).toFixed(0)}%</Badge>
                  </div>
                )}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 space-y-2 border-t border-slate-800 pt-3">
                    <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Sources</div>
                    {m.citations.map((c) => (
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
            ),
          )}
        </div>

        <form onSubmit={send} className="mt-4 flex gap-2 border-t border-slate-800 pt-4">
          <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question…" />
          <Button type="submit" loading={streaming}>
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}
