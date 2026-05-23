// Typed API client with bearer-auth + one-shot refresh on 401.
// Tokens are persisted in localStorage; the dev server proxies /api to the backend.

import type {
  DocumentList,
  DocumentRead,
  DocumentStatusResponse,
  MeResponse,
  RagAnswer,
  RetrievalStrategy,
  SearchResponse,
  TokenResponse,
  UploadResponse,
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
  uploadDocument: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<UploadResponse>("/documents", { method: "POST", formData: fd });
  },
  documentStatus: (id: string) => request<DocumentStatusResponse>(`/documents/${id}/status`),
  reindexDocument: (id: string) => request<DocumentRead>(`/documents/${id}/reindex`, { method: "POST" }),
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  // ── search + rag ──
  search: (data: { query: string; top_k: number; strategy: RetrievalStrategy; rerank: boolean }) =>
    request<SearchResponse>("/search", { method: "POST", body: data }),
  ragQuery: (data: { query: string; top_k: number; strategy: RetrievalStrategy; rerank: boolean }) =>
    request<RagAnswer>("/rag/query", { method: "POST", body: data }),
};
