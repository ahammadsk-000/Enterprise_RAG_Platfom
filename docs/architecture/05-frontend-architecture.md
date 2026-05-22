# 05 — Frontend Architecture

## 1. Stack

React 18 + TypeScript + Vite · TailwindCSS + shadcn/ui · **Zustand** (client state) ·
**React Query** (server state) · React Router · native WebSocket client.

## 2. Structure (feature-first)

```
src/
├── app/            # router, root providers (QueryClient, theme, auth), layout shells
├── components/     # design-system primitives (shadcn/ui) + shared composites
├── features/
│   ├── auth/       # login, SSO callback, session bootstrap
│   ├── chat/       # streaming chat, message list, citation chips, source drawer
│   ├── documents/  # uploader (drag/drop, batch), doc table, ingestion progress
│   ├── search/     # hybrid search explorer, filters, result inspection
│   ├── graph/      # knowledge-graph explorer (entities/relations)
│   ├── workspaces/ # workspace switcher, members, roles
│   └── admin/      # analytics: usage, cost, retrieval, system health, agent timeline
├── lib/            # apiClient (fetch+auth refresh), wsClient, queryClient, rbac
├── stores/         # zustand: auth, ui (theme/sidebar), chat session, workspace
├── hooks/          # useStreamingChat, useUpload, useWebSocket, usePermissions
├── types/          # shared API types (generated from OpenAPI)
└── styles/         # tailwind layers, themes (dark/light)
```

## 3. State model

- **Server state → React Query.** Documents, conversations, search results, analytics
  are fetched/cached/invalidated by React Query. No server data duplicated in Zustand.
- **Client state → Zustand.** Auth/session, theme + layout, active workspace, and the
  live streaming-chat buffer. Stores are small and sliced per concern.
- **Realtime → WebSocket hooks.** `useStreamingChat` appends tokens to the chat store;
  `useIngestionProgress` updates document status via WS push + React Query cache writes.

## 4. Streaming chat UX

- Open WS to `/api/v1/ws/chat/{conversationId}` with JWT.
- Render tokens incrementally; show retrieval/agent step indicators from trace events.
- Citation chips link to a **Source drawer** that previews the cited page/chunk with
  highlight (bbox/page from the citation payload). Confidence + faithfulness shown.

## 5. RBAC in the UI

- Permissions hydrated at login; `usePermissions()` + `<Can permission=...>` gate
  routes and actions. UI gating is convenience only — the backend is authoritative.

## 6. Types & contracts

- API types generated from the backend OpenAPI schema into `src/types` so the client
  stays in lockstep with the backend contract.

## 7. Quality

- Strict TS, ESLint + Prettier, Vitest + Testing Library for components/hooks,
  Playwright for the chat + upload e2e flows. Code-split per feature route.
