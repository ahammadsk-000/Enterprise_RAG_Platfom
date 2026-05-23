import { create } from "zustand";

import { api, tokenStore } from "@/lib/api";
import type { MeResponse, TokenResponse } from "@/types/api";

interface AuthState {
  me: MeResponse | null;
  status: "loading" | "authenticated" | "anonymous";
  hydrate: () => Promise<void>;
  onTokens: (tokens: TokenResponse) => Promise<void>;
  logout: () => void;
  hasPermission: (code: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  me: null,
  status: "loading",

  hydrate: async () => {
    if (!tokenStore.access) {
      set({ status: "anonymous", me: null });
      return;
    }
    try {
      const me = await api.me();
      set({ me, status: "authenticated" });
    } catch {
      tokenStore.clear();
      set({ status: "anonymous", me: null });
    }
  },

  onTokens: async (tokens) => {
    tokenStore.set(tokens);
    const me = await api.me();
    set({ me, status: "authenticated" });
  },

  logout: () => {
    tokenStore.clear();
    set({ me: null, status: "anonymous" });
  },

  hasPermission: (code) => {
    const me = get().me;
    return !!me && (me.user.is_superuser || me.permissions.includes(code));
  },
}));
