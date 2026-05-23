import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { Spinner } from "@/components/ui";
import { AdminPage } from "@/features/admin/AdminPage";
import { AgentsPage } from "@/features/agents/AgentsPage";
import { ChatPage } from "@/features/chat/ChatPage";
import { DocumentsPage } from "@/features/documents/DocumentsPage";
import { EvaluationPage } from "@/features/evaluation/EvaluationPage";
import { GraphPage } from "@/features/graph/GraphPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { SearchPage } from "@/features/search/SearchPage";
import { WorkspacesPage } from "@/features/workspaces/WorkspacesPage";
import { useAuthStore } from "@/stores/auth";

export default function App() {
  const status = useAuthStore((s) => s.status);
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  if (status === "loading") {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        <Spinner />
      </div>
    );
  }

  if (status === "anonymous") {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/workspaces" element={<WorkspacesPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </Layout>
  );
}
