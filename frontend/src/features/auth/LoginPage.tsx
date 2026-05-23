import { useState } from "react";

import { Button, Card, ErrorText, Input, Label } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

type Mode = "login" | "register";

export function LoginPage() {
  const onTokens = useAuthStore((s) => s.onTokens);
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const tokens =
        mode === "login"
          ? await api.login({ email, password })
          : await api.register({ email, password, full_name: fullName || undefined, organization_name: orgName });
      await onTokens(tokens);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-semibold text-white">Enterprise RAG Platform</h1>
          <p className="mt-1 text-sm text-slate-400">
            {mode === "login" ? "Sign in to your workspace" : "Create an organization"}
          </p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          {mode === "register" && (
            <div>
              <Label>Organization name</Label>
              <Input value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="Acme Corp" required />
            </div>
          )}
          {mode === "register" && (
            <div>
              <Label>Full name</Label>
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Doe" />
            </div>
          )}
          <div>
            <Label>Email</Label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />
          </div>
          <div>
            <Label>Password</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              minLength={8}
              required
            />
          </div>

          <ErrorText>{error}</ErrorText>

          <Button type="submit" loading={busy} className="w-full">
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <button
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
          className="mt-4 w-full text-center text-sm text-brand-400 hover:text-brand-500"
        >
          {mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}
        </button>
      </Card>
    </div>
  );
}
