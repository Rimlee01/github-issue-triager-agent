import { useState } from "react";
import { api } from "../services/api.js";
import { Button, CopyButton, Label, ProgressBar } from "./ui/index.jsx";

const CATEGORY_VARIANT = {
  bug: "bug", security: "security", performance: "performance",
  feature_request: "feature", documentation: "documentation", question: "question",
};

const PRIORITY_COLORS = {
  critical: { fg: "var(--color-danger-fg)", bg: "var(--color-danger-subtle)", border: "var(--color-danger-fg)" },
  high: { fg: "var(--color-attention-fg)", bg: "var(--color-attention-subtle)", border: "var(--color-attention-fg)" },
  medium: { fg: "var(--color-accent-fg)", bg: "var(--color-accent-subtle)", border: "var(--color-accent-fg)" },
  low: { fg: "var(--color-success-fg)", bg: "var(--color-success-subtle)", border: "var(--color-success-fg)" },
};

function SectionHeader({ children }) {
  return (
    <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "8px" }}>
      {children}
    </div>
  );
}

function InfoBox({ children }) {
  return (
    <div style={{ background: "var(--color-canvas-subtle)", border: "1px solid var(--color-border-muted)", borderRadius: "6px", padding: "12px 14px" }}>
      {children}
    </div>
  );
}

function FeedbackRow({ analysisId }) {
  const [voted, setVoted] = useState(null);
  const vote = async (score) => {
    try { await api.submitFeedback(analysisId, score); setVoted(score); } catch {}
  };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px 16px", borderTop: "1px solid var(--color-border-muted)" }}>
      <span style={{ fontSize: "13px", color: "var(--color-fg-muted)" }}>Was this helpful?</span>
      <Button variant={voted === 1 ? "primary" : "default"} size="sm" onClick={() => vote(1)} disabled={!!voted}>👍 Yes</Button>
      <Button variant={voted === -1 ? "danger" : "default"} size="sm" onClick={() => vote(-1)} disabled={!!voted}>👎 No</Button>
      {voted && <span style={{ fontSize: "12px", color: "var(--color-success-fg)" }}>Thanks for the feedback!</span>}
    </div>
  );
}

export default function ResultsDashboard({ result }) {
  const [prOpen, setPrOpen] = useState(false);

  if (!result) {
    return (
      <div style={{
        background: "var(--color-canvas-default)", border: "1px dashed var(--color-border-default)",
        borderRadius: "6px", padding: "60px 40px", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: "12px", minHeight: "400px",
      }}>
        <svg width="40" height="40" viewBox="0 0 16 16" fill="var(--color-border-default)">
          <path d="M11.93 8.5a4.002 4.002 0 01-7.86 0H.75a.75.75 0 010-1.5h3.32a4.002 4.002 0 017.86 0h3.32a.75.75 0 010 1.5h-3.32z"/>
        </svg>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--color-fg-default)", marginBottom: "4px" }}>No analysis yet</div>
          <div style={{ fontSize: "13px", color: "var(--color-fg-muted)" }}>Index a repository and run the triage agent to see AI-powered results here.</div>
        </div>
      </div>
    );
  }

  const pc = PRIORITY_COLORS[result.priority] || PRIORITY_COLORS.medium;

  return (
    <div style={{ background: "var(--color-canvas-default)", border: "1px solid var(--color-border-default)", borderRadius: "6px", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ padding: "16px", borderBottom: "1px solid var(--color-border-muted)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
          <span style={{ fontSize: "11px", color: "var(--color-fg-muted)" }}>#{result.issue_id?.slice(0,8)}</span>
          {result.processing_time_ms && (
            <span style={{ fontSize: "11px", color: "var(--color-fg-subtle)", marginLeft: "auto" }}>
              ⏱ {(result.processing_time_ms / 1000).toFixed(1)}s
            </span>
          )}
        </div>
        <h2 style={{ fontSize: "16px", fontWeight: 600, lineHeight: 1.4, marginBottom: "10px", color: "var(--color-fg-default)" }}>
          {result.summary}
        </h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
          <Label variant={CATEGORY_VARIANT[result.category] || "default"}>
            {result.category?.replace("_", " ")}
          </Label>
          <span style={{
            display: "inline-flex", alignItems: "center", padding: "0 8px", fontSize: "12px",
            fontWeight: 600, lineHeight: "20px", borderRadius: "100px",
            background: pc.bg, color: pc.fg, border: `1px solid ${pc.border}`,
          }}>
            {result.priority} priority
          </span>
          {result.duplicate_of && <Label variant="default">duplicate of #{result.duplicate_of.number}</Label>}
          {result.suggested_labels?.map(l => (
            <Label key={l} variant="default">{l}</Label>
          ))}
        </div>
      </div>

      <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "20px" }}>
        {/* Two column layout */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <SectionHeader>Technical area</SectionHeader>
              <InfoBox><span style={{ fontSize: "13px", fontWeight: 600 }}>{result.technical_area}</span></InfoBox>
            </div>
            <div>
              <SectionHeader>Priority reasoning</SectionHeader>
              <InfoBox><p style={{ fontSize: "13px", color: "var(--color-fg-muted)", lineHeight: 1.6, margin: 0 }}>{result.priority_reason}</p></InfoBox>
            </div>
            <div>
              <SectionHeader>Classification confidence</SectionHeader>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div style={{ flex: 1 }}>
                  <ProgressBar value={result.category_confidence}
                    color={result.category_confidence > 0.7 ? "var(--color-success-emphasis)" : "var(--color-attention-emphasis)"} />
                </div>
                <span style={{ fontSize: "12px", color: "var(--color-fg-muted)", minWidth: "32px" }}>
                  {Math.round(result.category_confidence * 100)}%
                </span>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <SectionHeader>Related files</SectionHeader>
              {result.related_files?.length ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  {result.related_files.slice(0, 5).map(f => (
                    <div key={f.path} style={{
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      padding: "6px 10px", background: "var(--color-canvas-subtle)",
                      border: "1px solid var(--color-border-muted)", borderRadius: "6px",
                    }}>
                      <code style={{ fontSize: "12px", color: "var(--color-accent-fg)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "78%" }}>
                        {f.path}
                      </code>
                      <span style={{ fontSize: "11px", color: "var(--color-fg-muted)", flexShrink: 0 }}>
                        {Math.round(f.relevance_score * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              ) : <p style={{ fontSize: "12px", color: "var(--color-fg-subtle)" }}>No related files found.</p>}
            </div>
            <div>
              <SectionHeader>Similar issues</SectionHeader>
              {result.similar_issues?.length ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  {result.similar_issues.slice(0, 3).map(s => (
                    <div key={s.number || s.title} style={{
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      padding: "6px 10px", background: "var(--color-canvas-subtle)",
                      border: `1px solid ${s.is_likely_duplicate ? "var(--color-done-fg)" : "var(--color-border-muted)"}`,
                      borderRadius: "6px",
                    }}>
                      <span style={{ fontSize: "12px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {s.number ? `#${s.number} ` : ""}{s.title}
                      </span>
                      <span style={{ fontSize: "11px", color: "var(--color-fg-muted)", flexShrink: 0, marginLeft: "8px" }}>
                        {Math.round(s.similarity_score * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              ) : <p style={{ fontSize: "12px", color: "var(--color-fg-subtle)" }}>No similar issues found.</p>}
            </div>
          </div>
        </div>

        {/* Solution */}
        <div>
          <SectionHeader>Suggested solution</SectionHeader>
          <InfoBox>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "4px" }}>Root cause</div>
                <p style={{ fontSize: "13px", margin: 0, lineHeight: 1.6 }}>{result.suggested_solution?.root_cause}</p>
              </div>
              <div>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "4px" }}>Suggested fix</div>
                <p style={{ fontSize: "13px", margin: 0, lineHeight: 1.6 }}>{result.suggested_solution?.suggested_fix}</p>
              </div>
              {result.suggested_solution?.files_to_modify?.length > 0 && (
                <div>
                  <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "6px" }}>Files to modify</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                    {result.suggested_solution.files_to_modify.map(f => (
                      <code key={f} style={{ fontSize: "12px", padding: "2px 8px", background: "var(--color-canvas-default)", border: "1px solid var(--color-border-default)", borderRadius: "6px" }}>
                        {f}
                      </code>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "4px" }}>Implementation approach</div>
                <p style={{ fontSize: "13px", margin: 0, lineHeight: 1.6 }}>{result.suggested_solution?.implementation_approach}</p>
              </div>
              <div>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "6px" }}>
                  Solution confidence — {Math.round((result.suggested_solution?.confidence_score || 0) * 100)}%
                </div>
                <ProgressBar value={result.suggested_solution?.confidence_score || 0}
                  color={(result.suggested_solution?.confidence_score || 0) > 0.6 ? "var(--color-success-emphasis)" : "var(--color-attention-emphasis)"} />
              </div>
            </div>
          </InfoBox>
        </div>

        {/* PR Description */}
        {result.pr_description && (
          <div>
            <SectionHeader>Pull request description</SectionHeader>
            <div style={{ border: "1px solid var(--color-border-default)", borderRadius: "6px", overflow: "hidden" }}>
              <div style={{ padding: "8px 12px", background: "var(--color-canvas-subtle)", borderBottom: prOpen ? "1px solid var(--color-border-muted)" : "none", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "12px", color: "var(--color-fg-muted)" }}>Ready to use as a PR description</span>
                <div style={{ display: "flex", gap: "6px" }}>
                  <Button variant="default" size="sm" onClick={() => setPrOpen(!prOpen)}>{prOpen ? "Hide" : "Preview"}</Button>
                  <CopyButton text={result.pr_description} />
                </div>
              </div>
              {prOpen && (
                <pre style={{ margin: 0, padding: "12px 14px", fontSize: "12px", whiteSpace: "pre-wrap", color: "var(--color-fg-default)", fontFamily: "var(--font-mono)", maxHeight: "240px", overflowY: "auto", lineHeight: 1.6 }}>
                  {result.pr_description}
                </pre>
              )}
            </div>
          </div>
        )}

        {/* Generated Reply */}
        <div>
          <SectionHeader>Generated GitHub reply</SectionHeader>
          <div style={{ border: "1px solid var(--color-border-default)", borderRadius: "6px", overflow: "hidden" }}>
            <div style={{ padding: "8px 12px", background: "var(--color-canvas-subtle)", borderBottom: "1px solid var(--color-border-muted)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "var(--color-accent-emphasis)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <span style={{ color: "#fff", fontSize: "11px", fontWeight: 700 }}>AI</span>
                </div>
                <span style={{ fontSize: "12px", fontWeight: 600 }}>Issue Triager</span>
                <span style={{ fontSize: "12px", color: "var(--color-fg-muted)" }}>just now</span>
              </div>
              <CopyButton text={result.generated_response} label="Copy reply" />
            </div>
            <div style={{ padding: "14px 16px", fontSize: "14px", lineHeight: 1.7, color: "var(--color-fg-default)", whiteSpace: "pre-wrap" }}>
              {result.generated_response}
            </div>
          </div>
        </div>

        {/* Reasoning trace */}
        <div>
          <SectionHeader>Reasoning trace</SectionHeader>
          <div style={{ borderLeft: "2px solid var(--color-border-muted)", paddingLeft: "16px", display: "flex", flexDirection: "column", gap: "10px" }}>
            {result.reasoning_trace?.map((line, i) => (
              <div key={i} style={{ position: "relative", fontSize: "12px", color: "var(--color-fg-muted)", lineHeight: 1.5 }}>
                <div style={{
                  position: "absolute", left: "-22px", top: "4px", width: "8px", height: "8px",
                  borderRadius: "50%", background: "var(--color-success-emphasis)",
                  border: "2px solid var(--color-canvas-default)",
                }}/>
                {line}
              </div>
            ))}
          </div>
        </div>
      </div>

      <FeedbackRow analysisId={result.issue_id} />
    </div>
  );
}
