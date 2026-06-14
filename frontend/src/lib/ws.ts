// WebSocket client for streaming chat. Connects through the same origin so the
// Vite dev proxy (ws: true) / nginx forwards the upgrade to the backend.

import { tokenStore } from "@/lib/api";
import type { ChatStreamEvent } from "@/types/api";

export function openChatSocket(
  conversationId: string,
  handlers: {
    onEvent: (event: ChatStreamEvent) => void;
    onOpen?: () => void;
    onClose?: () => void;
  },
): WebSocket {
  const token = encodeURIComponent(tokenStore.access ?? "");
  // VITE_API_BASE (set on Vercel) points to the backend origin in production. In dev
  // we use the page's host so the Vite proxy (ws: true) forwards the upgrade.
  const apiBase = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
  let wsBase: string;
  if (apiBase) {
    wsBase = apiBase.replace(/^http/, "ws"); // http(s):// -> ws(s)://
  } else {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    wsBase = `${proto}://${window.location.host}`;
  }
  const url = `${wsBase}/api/v1/ws/chat/${conversationId}?token=${token}`;
  const socket = new WebSocket(url);

  socket.onopen = () => handlers.onOpen?.();
  socket.onclose = () => handlers.onClose?.();
  socket.onmessage = (msg) => {
    try {
      handlers.onEvent(JSON.parse(msg.data) as ChatStreamEvent);
    } catch {
      /* ignore malformed frame */
    }
  };
  return socket;
}
