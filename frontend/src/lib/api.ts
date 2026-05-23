// Typed API client with bearer-auth + one-shot refresh on 401.
// Tokens are persisted in localStorage; the dev server proxies /api to the backend.

import type {
  AgentResearchResponse,
  AnalyticsOverview,
  ChatMessage,
  Conversation,
  DocumentContent,
  DocumentList,
  DocumentRead,
  DocumentStatusResponse,
  EvalDataset,
  EvalRunResult,
  EvalSampleIn,
  GraphExploreResponse,
  MeResponse,
  RagAnswer,
  RetrievalStrategy,
  SearchResponse,
  TokenResponse,
  UploadResponse,
  Workspace,
} from "@/types/api";

const BASE = "/api/v1";
const ACCESS_KEY = "rag.access_token";
const REFRESH_KEY = "rag.refresh_token";

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(tokens: TokenResponse) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public traceId?: string,
  ) {
    super(message);
  }
}

async function parseError(resp: Response): Promise<ApiError> {
  let detail = resp.statusText;
  let traceId: string | undefined;
  try {
    const body = await resp.json();
    detail = body.detail ?? body.title ?? detail;
    traceId = body.trace_id;
  } catch {
    /* non-JSON error */
  }
  return new ApiError(resp.status, detail, traceId);
}

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const resp = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) {
    tokenStore.clear();
    return false;
  }
  tokenStore.set((await resp.json()) as TokenResponse);
  return true;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  auth?: boolean;
  retry?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, auth = true, retry = true } = opts;
  const headers: Record<string, string> = {};
  if (auth && tokenStore.access) headers.Authorization = `Bearer ${tokenStore.access}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
  });

  if (resp.status === 401 && auth && retry && (await refreshTokens())) {
    return request<T>(path, { ...opts, retry: false });
  }
  if (!resp.ok) throw await parseError(resp);
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  // ── auth ──
  register: (data: { email: string; password: string; full_name?: string; organization_name: string }) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: data, auth: false }),
  login: (data: { email: string; password: string; organization_slug?: string }) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: data, auth: false }),
  me: () => request<MeResponse>("/auth/me"),

  // ── documents ──
  listDocuments: (limit = 50, offset = 0) =>
    request<DocumentList>(`/documents?limit=${limit}&offset=${offset}`),
  uploadDocument: (file: File, workspaceId?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    const qs = workspaceId ? `?workspace_id=${workspaceId}` : "";
    return request<UploadResponse>(`/documents${qs}`, { method: "POST", formData: fd });
  },
  documentStatus: (id: string) => request<DocumentStatusResponse>(`/documents/${id}/status`),
  reindexDocument: (id: string) => request<DocumentRead>(`/documents/${id}/reindex`, { method: "POST" }),
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  getDocumentContent: (id: string) => request<DocumentContent>(`/documents/${id}/content`),
  saveDocumentContent: (id: string, content: string) =>
    request<DocumentRead>(`/documents/${id}/content`, { method: "PUT", body: { content } }),

  // ── search + rag ──
  search: (data: {
    query: string;
    top_k: number;
    strategy: RetrievalStrategy;
    rerank: boolean;
    workspace_id?: string;
  }) => request<SearchResponse>("/search", { method: "POST", body: data }),
  ragQuery: (data: { query: string; top_k: number; strategy: RetrievalStrategy; rerank: boolean }) =>
    request<RagAnswer>("/rag/query", { method: "POST", body: data }),

  // ── ai assist (inline completion) ──
  assistComplete: (prefix: string, language?: string) =>
    request<{ completion: string }>("/assist/complete", { method: "POST", body: { prefix, language } }),

  // ── workspaces ──
  listWorkspaces: () => request<Workspace[]>("/workspaces"),
  createWorkspace: (data: { name: string; description?: string; chunking_strategy?: string }) =>
    request<Workspace>("/workspaces", { method: "POST", body: data }),
  deleteWorkspace: (id: string) => request<void>(`/workspaces/${id}`, { method: "DELETE" }),

  // ── graph rag ──
  graphExplore: (data: { query: string; hops: number; limit?: number }) =>
    request<GraphExploreResponse>("/graph/explore", { method: "POST", body: data }),

  // ── agents ──
  agentResearch: (data: { query: string; top_k: number; workspace_id?: string }) =>
    request<AgentResearchResponse>("/agents/research", { method: "POST", body: data }),

  // ── evaluation ──
  listDatasets: () => request<EvalDataset[]>("/evaluation/datasets"),
  createDataset: (data: { name: string; kind?: string; samples: EvalSampleIn[] }) =>
    request<EvalDataset>("/evaluation/datasets", { method: "POST", body: data }),
  runEvaluation: (datasetId: string) =>
    request<EvalRunResult>(`/evaluation/datasets/${datasetId}/run`, { method: "POST" }),

  // ── admin analytics ──
  analyticsOverview: () => request<AnalyticsOverview>("/admin/analytics/overview"),

  // ── chat conversations ──
  listConversations: () => request<Conversation[]>("/chat/conversations"),
  createConversation: (data: { title?: string; workspace_id?: string }) =>
    request<Conversation>("/chat/conversations", { method: "POST", body: data }),
  listMessages: (conversationId: string) =>
    request<ChatMessage[]>(`/chat/conversations/${conversationId}/messages`),
};

// Download the raw stored file (auth header required, so not a plain anchor href).
export async function downloadDocumentFile(id: string, filename: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (tokenStore.access) headers.Authorization = `Bearer ${tokenStore.access}`;
  const resp = await fetch(`${BASE}/documents/${id}/download`, { headers });
  if (!resp.ok) throw new ApiError(resp.status, "Download failed");
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
