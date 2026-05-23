// API contract types mirroring the backend Pydantic schemas.

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserRead {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  auth_provider: string;
  last_login_at: string | null;
  created_at: string;
}

export interface MeResponse {
  user: UserRead;
  organization_id: string | null;
  role: string | null;
  permissions: string[];
}

export type DocumentStatus =
  | "uploaded"
  | "parsing"
  | "parsed"
  | "chunking"
  | "chunked"
  | "embedding"
  | "indexed"
  | "failed";

export interface DocumentRead {
  id: string;
  organization_id: string;
  workspace_id: string | null;
  title: string;
  mime_type: string;
  byte_size: number;
  content_hash: string;
  status: DocumentStatus;
  language: string | null;
  page_count: number | null;
  error: string | null;
  created_at: string;
}

export interface DocumentList {
  items: DocumentRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadResponse {
  document: DocumentRead;
  duplicate: boolean;
}

export interface IngestionJobRead {
  id: string;
  stage: string;
  status: string;
  attempts: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface DocumentStatusResponse {
  document_id: string;
  status: DocumentStatus;
  chunk_count: number;
  jobs: IngestionJobRead[];
}

export type RetrievalStrategy = "dense" | "bm25" | "hybrid";

export interface SearchHit {
  chunk_id: string;
  document_id: string;
  content: string;
  score: number;
  source: string;
  page_from: number | null;
  chunk_type: string;
}

export interface SearchResponse {
  query: string;
  strategy: RetrievalStrategy;
  hits: SearchHit[];
  latency_ms: number;
}

export interface Citation {
  marker: number;
  chunk_id: string;
  document_id: string;
  page_from: number | null;
  snippet: string;
  score: number;
}

export interface RagAnswer {
  answer: string;
  citations: Citation[];
  confidence: number;
  model: string;
  strategy: RetrievalStrategy;
  retrieved: number;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
}

export interface ProblemDetail {
  title?: string;
  detail?: string;
  status?: number;
  trace_id?: string;
}
