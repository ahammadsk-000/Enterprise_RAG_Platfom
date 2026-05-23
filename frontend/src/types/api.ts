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

// ── workspaces ──
export interface Workspace {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
  chunking_strategy: string;
  created_at: string;
}

// ── graph rag ──
export interface GraphNeighbor {
  name: string;
  type: string;
  relation: string;
  direction: string;
}

export interface GraphExploreResponse {
  seeds: string[];
  neighbors: GraphNeighbor[];
}

// ── agents ──
export interface AgentStep {
  node: string;
  role: string;
  output: Record<string, unknown>;
  latency_ms: number;
}

export interface AgentResearchResponse {
  run_id: string | null;
  answer: string;
  citations: Citation[];
  confidence: number;
  verified: boolean;
  sub_questions: string[];
  steps: AgentStep[];
  total_tokens: number;
}

// ── evaluation ──
export interface EvalDataset {
  id: string;
  name: string;
  kind: string;
  created_at: string;
}

export interface EvalSampleIn {
  question: string;
  ground_truth?: string | null;
  contexts: string[];
}

export interface SampleResult {
  sample_id: string;
  question: string;
  answer: string;
  scores: Record<string, number>;
}

export interface EvalRunResult {
  run_id: string | null;
  dataset_id: string;
  metrics: Record<string, number>;
  sample_count: number;
  results: SampleResult[];
}

// ── admin analytics ──
export interface AnalyticsOverview {
  documents_total: number;
  documents_indexed: number;
  conversations: number;
  messages: number;
  total_tokens: number;
  avg_confidence: number | null;
  retrieval_queries: number;
  avg_retrieval_latency_ms: number | null;
  agent_runs: number;
}

// ── chat ──
export interface Conversation {
  id: string;
  title: string;
  workspace_id: string | null;
  last_message_at: string | null;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  model: string | null;
  confidence: number | null;
  citations: Citation[];
  created_at: string;
}

// WebSocket streaming events
export type ChatStreamEvent =
  | { type: "token"; content: string }
  | { type: "done"; message_id: string; citations: Citation[]; confidence: number; model: string; latency_ms: number }
  | { type: "error"; detail: string };
