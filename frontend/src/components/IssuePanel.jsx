import { useRef, useState } from "react";
import { api, createSSE } from "../services/api.js";
import { Button, Input, Spinner, Textarea } from "./ui/index.jsx";

const NODES = [
  { id: "issue_analyzer", label: "Issue Analyzer" },
  { id: "repo_context", label: "Repository Context" },
  { id: "classification", label: "Classification" },
  { id: "priority", label: "Priority Assessment" },
  { id: "solution", label: "Solution Suggestion" },
  { id: "pr", label: "PR Description" },
  { id: "response", label: "Response Generator" },
];

export default function IssuePanel({ repo, onResult }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nodeStates, setNodeStates] = useState([]);
  const sseRef = useRef(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!repo || repo.status !== "ready") { setError("Index a repository first."); return; }
    if (!title.trim()) { setError("Please enter an issue title."); return; }
    if (!description.trim()) { setError("Please enter an issue description."); return; }

    setLoading(true);
    setError(null);
    setNodeStates(NODES.map(n => ({ ...n, state: "pending", summary: "" })));

    const analysisId = crypto.randomUUID();

    // Create a promise that resolves when the SSE stream signals "done"
    // This ensures we don't close the connection before all events are processed.
    let sseResolve;
    const sseDone = new Promise(resolve => { sseResolve = resolve; });

    // Connect SSE first
    sseRef.current = createSSE(analysisId, (msg) => {
      if (msg.type === "node_start") {
        setNodeStates(prev => prev.map((n, i) =>
          i === msg.index ? { ...n, state: "active" } : n
        ));
      } else if (msg.type === "node_complete") {
        setNodeStates(prev => prev.map((n, i) =>
          i === msg.index ? { ...n, state: "done", summary: msg.summary } : n
        ));
      } else if (msg.type === "done") {
        // All nodes finished — mark any stragglers as done (preserving summaries)
        setNodeStates(prev => prev.map(n => ({ ...n, state: "done" })));
        sseResolve();
      } else if (msg.type === "error") {
        sseResolve();
      }
    });

    // Small delay to ensure SSE connection is established before analysis starts
    await new Promise(r => setTimeout(r, 300));

    try {
      // Fire the HTTP request and wait for both it AND the SSE stream to finish.
      // The HTTP response carries the result data, while the SSE stream drives
      // the step-by-step animation. We need both to complete.
      const [result] = await Promise.all([
        api.analyzeIssue({
          issueTitle: title.trim(),
          issueDescription: description.trim(),
          repoId: repo.repo_id,
          analysisId,
        }),
        sseDone,
      ]);
      onResult(result);
    } catch (err) {
      setError(err.message);
      setNodeStates([]);
    } finally {
      sseRef.current?.close();
      setLoading(false);
    }
  }

  const PRIORITY_COLOR = { critical: "var(--color-danger-fg)", high: "var(--color-attention-fg)", medium: "var(--color-accent-fg)", low: "var(--color-success-fg)" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Issue Form */}
      <div style={{ background: "var(--color-canvas-default)", border: "1px solid var(--color-border-default)", borderRadius: "6px", overflow: "hidden" }}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--color-border-muted)", background: "var(--color-canvas-subtle)", display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-fg-default)" }}>New issue triage</span>
        </div>
        <form onSubmit={handleSubmit} style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>
            <label style={{ display: "block", fontSize: "14px", fontWeight: 600, marginBottom: "6px" }}>Title <span style={{ color: "var(--color-danger-fg)" }}>*</span></label>
            <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Short descriptive summary of the issue" disabled={loading} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "14px", fontWeight: 600, marginBottom: "6px" }}>Description <span style={{ color: "var(--color-danger-fg)" }}>*</span></label>
            <Textarea value={description} onChange={e => setDescription(e.target.value)}
              placeholder={"Steps to reproduce:\n1. \n2. \n\nExpected behavior:\n\nActual behavior:"}
              disabled={loading} rows={7} />
          </div>
          <Button type="submit" disabled={loading} variant="accent" style={{ width: "100%", padding: "8px 16px", fontSize: "14px" }}>
            {loading ? <><Spinner size={14} color="#fff" /> Running triage agent…</> : "▶  Run triage agent"}
          </Button>
          {error && (
            <div style={{ padding: "8px 12px", background: "var(--color-danger-subtle)", border: "1px solid var(--color-danger-fg)", borderRadius: "6px", color: "var(--color-danger-fg)", fontSize: "13px" }}>
              {error}
            </div>
          )}
        </form>
      </div>

      {/* Agent pipeline progress */}
      {nodeStates.length > 0 && (
        <div style={{ background: "var(--color-canvas-default)", border: "1px solid var(--color-border-default)", borderRadius: "6px", overflow: "hidden" }}>
          <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--color-border-muted)", background: "var(--color-canvas-subtle)" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Agent pipeline
            </span>
          </div>
          <div style={{ padding: "8px 0" }}>
            {nodeStates.map((node, i) => (
              <div key={node.id} style={{ display: "flex", alignItems: "flex-start", gap: "12px", padding: "8px 16px" }}>
                <div style={{ marginTop: "2px", flexShrink: 0 }}>
                  {node.state === "done" ? (
                    <div style={{ width: "18px", height: "18px", borderRadius: "50%", background: "var(--color-success-emphasis)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M2 5l2.5 2.5L8 3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                  ) : node.state === "active" ? (
                    <Spinner size={18} color="var(--color-accent-fg)" />
                  ) : (
                    <div style={{ width: "18px", height: "18px", borderRadius: "50%", border: "2px solid var(--color-border-default)" }}/>
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: "13px", fontWeight: node.state === "active" ? 600 : 400,
                    color: node.state === "pending" ? "var(--color-fg-subtle)" : "var(--color-fg-default)",
                  }}>
                    {node.label}
                  </div>
                  {node.summary && (
                    <div style={{ fontSize: "12px", color: "var(--color-fg-muted)", marginTop: "2px" }}>
                      {node.summary}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
