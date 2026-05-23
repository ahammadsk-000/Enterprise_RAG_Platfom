import { create } from "zustand";

// Active workspace selection (persisted). null = "All / no workspace filter".
const KEY = "rag.active_workspace";

interface WorkspaceState {
  activeId: string | null;
  setActive: (id: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  activeId: localStorage.getItem(KEY) || null,
  setActive: (id) => {
    if (id) localStorage.setItem(KEY, id);
    else localStorage.removeItem(KEY);
    set({ activeId: id });
  },
}));
