import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useAuthStore } from "@/stores/auth";

const NAV = [
  { to: "/chat", label: "Chat", icon: "💬" },
  { to: "/search", label: "Search", icon: "🔍" },
  { to: "/documents", label: "Documents", icon: "📄" },
];

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
        <nav className="flex flex-1 flex-col gap-1">
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
