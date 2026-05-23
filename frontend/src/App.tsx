import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { Spinner } from "@/components/ui";
import { ChatPage } from "@/features/chat/ChatPage";
import { DocumentsPage } from "@/features/documents/DocumentsPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { SearchPage } from "@/features/search/SearchPage";
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
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </Layout>
  );
}
