"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { API_BASE_URL } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey }),
      });

      if (!res.ok) {
        setError("Invalid API key");
        return;
      }

      const data = await res.json();
      if (!data.valid) {
        setError("Invalid API key");
        return;
      }

      document.cookie = `adforge_api_key=${encodeURIComponent(apiKey)}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Lax`;
      router.push("/dashboard");
    } catch {
      setError("Failed to validate. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-sm text-center">
        <h1 className="text-page-title">ADFORGE</h1>
        <p className="text-label text-muted-foreground mt-2">
          CREATIVE INFRASTRUCTURE
        </p>
        <form onSubmit={handleSubmit} className="mt-12 space-y-6">
          <Input
            type="password"
            placeholder="API Key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            required
            autoFocus
          />
          {error && (
            <p className="text-label text-destructive">{error}</p>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "VALIDATING..." : "SIGN IN"}
          </Button>
        </form>
      </div>
    </div>
  );
}
