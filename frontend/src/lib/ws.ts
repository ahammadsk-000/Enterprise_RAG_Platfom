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
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const token = encodeURIComponent(tokenStore.access ?? "");
  const url = `${proto}://${window.location.host}/api/v1/ws/chat/${conversationId}?token=${token}`;
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
