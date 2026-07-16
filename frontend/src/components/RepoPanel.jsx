import { useEffect, useState } from "react";
import { api } from "../services/api.js";
import { Button, Input, Spinner } from "./ui/index.jsx";

export default function RepoPanel({ repo, onRepoReady }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Prefill the repository URL if the repo has already been indexed
  useEffect(() => {
    if (repo && repo.status === "ready" && !url) {
      setUrl(`https://github.com/${repo.owner}/${repo.name}`);
    }
  }, [repo]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!url.trim()) {
      setError("Please enter a repository URL.");
      return;
    }
    setLoading(true); setError(null);
    try {
      const result = await api.analyzeRepository(url.trim());
      onRepoReady(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ background: "var(--color-canvas-default)", border: "1px solid var(--color-border-default)", borderRadius: "6px", overflow: "hidden" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--color-border-muted)", background: "var(--color-canvas-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "13px", fontWeight: 600 }}>Repository</span>
        {repo && (
          <span style={{
            fontSize: "11px", padding: "1px 8px", borderRadius: "100px", fontWeight: 500,
            background: repo.status === "ready" ? "var(--color-success-subtle)" : "var(--color-attention-subtle)",
            color: repo.status === "ready" ? "var(--color-success-fg)" : "var(--color-attention-fg)",
            border: `1px solid ${repo.status === "ready" ? "var(--color-success-emphasis)" : "var(--color-attention-emphasis)"}`,
          }}>
            {repo.status}
          </span>
        )}
      </div>
      <div style={{ padding: "16px" }}>
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "8px" }}>
          <Input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://github.com/owner/repo" disabled={loading} />
          <Button type="submit" variant="default" disabled={loading} style={{ whiteSpace: "nowrap", flexShrink: 0 }}>
            {loading ? <Spinner size={14} /> : "Index"}
          </Button>
        </form>
        {error && (
          <div style={{ marginTop: "10px", padding: "8px 12px", background: "var(--color-danger-subtle)", border: "1px solid var(--color-danger-fg)", borderRadius: "6px", color: "var(--color-danger-fg)", fontSize: "12px" }}>
            {error}
          </div>
        )}
        {repo && (
          <div style={{ marginTop: "12px", display: "flex", alignItems: "center", gap: "10px", padding: "10px 12px", background: "var(--color-canvas-subtle)", border: "1px solid var(--color-border-muted)", borderRadius: "6px" }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="var(--color-fg-muted)">
              <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
            </svg>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-accent-fg)" }}>{repo.owner}/{repo.name}</div>
              <div style={{ fontSize: "11px", color: "var(--color-fg-muted)", marginTop: "2px" }}>
                {repo.files_ingested} files · {repo.issues_ingested} issues · {repo.pull_requests_ingested} PRs indexed
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
