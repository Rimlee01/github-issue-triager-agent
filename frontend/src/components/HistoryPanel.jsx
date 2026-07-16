import { useEffect, useState } from "react";
import { api } from "../services/api.js";
import { Spinner } from "./ui/index.jsx";

const PRIORITY_COLORS = {
  critical: { bg: "#ffebe9", color: "#cf222e", border: "#ff818266" },
  high: { bg: "#fff8c5", color: "#9a6700", border: "#f2cc6066" },
  medium: { bg: "#ddf4ff", color: "#0969da", border: "#79c0ff66" },
  low: { bg: "#dafbe1", color: "#1a7f37", border: "#56d36466" },
};

const CATEGORY_COLORS = {
  bug: { bg: "#ffebe9", color: "#cf222e" },
  security: { bg: "#ffebe9", color: "#cf222e" },
  performance: { bg: "#fff8c5", color: "#9a6700" },
  feature_request: { bg: "#ddf4ff", color: "#0969da" },
  documentation: { bg: "#f6f8fa", color: "#57606a" },
  question: { bg: "#ddf4ff", color: "#0969da" },
};

export default function HistoryPanel({ repo }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!repo || repo.status !== "ready") return;
    setLoading(true);
    api.getHistory(repo.repo_id).then(setHistory).catch(() => {}).finally(() => setLoading(false));
  }, [repo?.repo_id]);

  if (!repo) return null;

  return (
    <div style={{ background: "var(--color-canvas-default)", border: "1px solid var(--color-border-default)", borderRadius: "6px", overflow: "hidden" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--color-border-muted)", background: "var(--color-canvas-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "13px", fontWeight: 600 }}>Analysis history</span>
        <span style={{ fontSize: "12px", color: "var(--color-fg-muted)" }}>{repo.owner}/{repo.name}</span>
      </div>

      {loading && (
        <div style={{ padding: "30px", display: "flex", justifyContent: "center" }}>
          <Spinner size={20} />
        </div>
      )}

      {!loading && history.length === 0 && (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--color-fg-muted)", fontSize: "13px" }}>
          No analyses yet for this repository.
        </div>
      )}

      {history.map((item, i) => {
        const pc = PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.medium;
        const cc = CATEGORY_COLORS[item.category] || { bg: "#f6f8fa", color: "#57606a" };
        return (
          <div key={item.issue_id} style={{
            padding: "12px 16px",
            borderBottom: i < history.length - 1 ? "1px solid var(--color-border-muted)" : "none",
            display: "flex", alignItems: "flex-start", gap: "12px",
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: "14px", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: "6px" }}>
                {item.issue_title}
              </div>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
                {item.category && (
                  <span style={{ fontSize: "11px", fontWeight: 500, padding: "0 7px", lineHeight: "20px", borderRadius: "100px", background: cc.bg, color: cc.color, border: `1px solid ${cc.color}44` }}>
                    {item.category.replace("_", " ")}
                  </span>
                )}
                {item.priority && (
                  <span style={{ fontSize: "11px", fontWeight: 500, padding: "0 7px", lineHeight: "20px", borderRadius: "100px", background: pc.bg, color: pc.color, border: `1px solid ${pc.border}` }}>
                    {item.priority}
                  </span>
                )}
                {item.processing_time_ms && (
                  <span style={{ fontSize: "11px", color: "var(--color-fg-subtle)" }}>⏱ {(item.processing_time_ms / 1000).toFixed(1)}s</span>
                )}
                {item.feedback_score === 1 && <span style={{ fontSize: "12px" }}>👍</span>}
                {item.feedback_score === -1 && <span style={{ fontSize: "12px" }}>👎</span>}
              </div>
            </div>
            <div style={{ fontSize: "11px", color: "var(--color-fg-subtle)", whiteSpace: "nowrap", flexShrink: 0 }}>
              {new Date(item.created_at).toLocaleDateString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}
