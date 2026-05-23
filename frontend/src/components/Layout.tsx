import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useWorkspaceStore } from "@/stores/workspace";

const NAV = [
  { to: "/chat", label: "Chat", icon: "💬" },
  { to: "/search", label: "Search", icon: "🔍" },
  { to: "/documents", label: "Documents", icon: "📄" },
  { to: "/graph", label: "Graph", icon: "🕸️" },
  { to: "/agents", label: "Agents", icon: "🤖" },
  { to: "/evaluation", label: "Evaluation", icon: "📊" },
  { to: "/workspaces", label: "Workspaces", icon: "🗂️" },
  { to: "/admin", label: "Admin", icon: "📈" },
];

function WorkspaceSwitcher() {
  const { activeId, setActive } = useWorkspaceStore();
  const workspaces = useQuery({ queryKey: ["workspaces"], queryFn: () => api.listWorkspaces() });

  return (
    <div className="mb-4 px-2">
      <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">
        Workspace
      </label>
      <select
        value={activeId ?? ""}
        onChange={(e) => setActive(e.target.value || null)}
        className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-brand-500"
      >
        <option value="">All documents</option>
        {workspaces.data?.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
      </select>
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const me = useAuthStore((s) => s.me);
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="flex h-full">
      <aside className="flex w-60 flex-col border-r border-slate-800 bg-slate-900/50 p-4">
        <div className="mb-6 px-2">
          <div className="text-lg font-semibold text-white">Enterprise RAG</div>
          <div className="text-xs text-slate-500">Knowledge Platform</div>
        </div>

        <WorkspaceSwitcher />

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition ${
                  isActive ? "bg-brand-600 text-white" : "text-slate-300 hover:bg-slate-800"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto border-t border-slate-800 pt-4">
          <div className="px-2 text-sm text-slate-200">{me?.user.email}</div>
          <div className="px-2 text-xs capitalize text-slate-500">{me?.role ?? "member"}</div>
          <button
            onClick={logout}
            className="mt-2 w-full rounded-md px-3 py-2 text-left text-sm text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
