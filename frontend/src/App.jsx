import { useEffect, useState } from "react";
import RepoPanel from "./components/RepoPanel.jsx";
import IssuePanel from "./components/IssuePanel.jsx";
import ResultsDashboard from "./components/ResultsDashboard.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";
import StatsChart from "./components/StatsChart.jsx";
import { api } from "./services/api.js";

function OctocatIcon() {
  return (
    <svg height="24" width="24" viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
    </svg>
  );
}

function Header({ theme, onToggle, repo, activeTab, onTabChange }) {
  return (
    <header style={{
      position: "sticky", top: 0, zIndex: 100,
      background: "var(--color-canvas-default)",
      borderBottom: "1px solid var(--color-border-default)",
    }}>
      <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "0 24px", height: "56px", display: "flex", alignItems: "center", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--color-fg-default)" }}>
          <OctocatIcon />
          <span style={{ fontWeight: 600, fontSize: "14px" }}>Issue Triager</span>
          <span style={{ color: "var(--color-border-default)" }}>/</span>
          <span style={{ fontSize: "14px", color: "var(--color-fg-muted)" }}>AI Agent · LangGraph · RAG · Groq</span>
        </div>

        <div style={{ flex: 1 }} />

        {repo && (
          <nav style={{ display: "flex", gap: "0" }}>
            {["triage", "history"].map(tab => (
              <button key={tab} onClick={() => onTabChange(tab)} style={{
                padding: "6px 14px", fontSize: "14px", cursor: "pointer",
                background: "none", border: "none",
                color: activeTab === tab ? "var(--color-fg-default)" : "var(--color-fg-muted)",
                borderBottom: activeTab === tab ? "2px solid var(--color-attention-emphasis)" : "2px solid transparent",
                fontWeight: activeTab === tab ? 600 : 400,
                textTransform: "capitalize", marginBottom: "-1px",
              }}>
                {tab === "history" ? "📋 History" : "🔬 Triage"}
              </button>
            ))}
          </nav>
        )}

        <button onClick={onToggle} style={{
          width: "32px", height: "32px", borderRadius: "6px", border: "1px solid var(--color-border-default)",
          background: "var(--color-canvas-default)", cursor: "pointer", fontSize: "16px",
          display: "flex", alignItems: "center", justifyContent: "center",
        }} title="Toggle theme">
          {theme === "dark" ? "☀️" : "🌙"}
        </button>
      </div>
    </header>
  );
}

function OnboardingBanner({ onDismiss }) {
  return (
    <div style={{
      background: "var(--color-accent-subtle)", border: "1px solid var(--color-accent-fg)",
      borderRadius: "6px", padding: "12px 16px", marginBottom: "16px",
      display: "flex", gap: "12px", alignItems: "flex-start",
    }}>
      <span style={{ fontSize: "18px", flexShrink: 0 }}>👋</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: "13px", color: "var(--color-accent-fg)", marginBottom: "4px" }}>
          Welcome to Issue Triager
        </div>
        <div style={{ fontSize: "13px", color: "var(--color-fg-muted)", lineHeight: 1.6 }}>
          <strong>Step 1:</strong> Paste a GitHub repo URL and click "Index" — builds a semantic knowledge base from the codebase.<br />
          <strong>Step 2:</strong> Describe an issue and click "Run triage agent" — a 7-node LangGraph agent classifies, prioritizes, suggests a fix, and drafts a GitHub reply in real-time.
        </div>
      </div>
      <button onClick={onDismiss} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-fg-muted)", fontSize: "18px", flexShrink: 0, lineHeight: 1 }}>×</button>
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "light");
  const [repo, setRepo] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState("triage");
  const [showOnboarding, setShowOnboarding] = useState(() => !localStorage.getItem("onboarding_dismissed"));

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  function handleRepoReady(r) {
    setRepo(r);
    setResult(null);
    if (r.status === "ready") refreshHistory(r.repo_id);
  }

  async function refreshHistory(repoId) {
    try { setHistory(await api.getHistory(repoId)); } catch {}
  }

  function handleResult(r) {
    setResult(r);
    if (repo) refreshHistory(repo.repo_id);
  }

  function handleTabChange(tab) {
    setActiveTab(tab);
    if (tab === "history" && repo) refreshHistory(repo.repo_id);
  }

  function dismissOnboarding() {
    setShowOnboarding(false);
    localStorage.setItem("onboarding_dismissed", "1");
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header theme={theme} onToggle={() => setTheme(t => t === "dark" ? "light" : "dark")}
        repo={repo} activeTab={activeTab} onTabChange={handleTabChange} />

      <main style={{ flex: 1, maxWidth: "1280px", width: "100%", margin: "0 auto", padding: "24px 24px 60px" }}>
        {showOnboarding && <OnboardingBanner onDismiss={dismissOnboarding} />}

        {activeTab === "triage" ? (
          <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: "20px", alignItems: "start" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <RepoPanel repo={repo} onRepoReady={handleRepoReady} />
              <IssuePanel repo={repo} onResult={handleResult} />
            </div>
            <ResultsDashboard result={result} />
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {history.length > 0 && <StatsChart history={history} />}
            <HistoryPanel repo={repo} />
          </div>
        )}
      </main>

      <footer style={{ padding: "16px 24px", borderTop: "1px solid var(--color-border-muted)", background: "var(--color-canvas-default)" }}>
        <div style={{ maxWidth: "1280px", margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "12px", color: "var(--color-fg-subtle)" }}>
            GitHub Issue Triager Agent · LangGraph + RAG + Groq Llama 3.3
          </span>
          <a href="https://github.com/Rimlee01/github-issue-triager-agent" target="_blank" rel="noreferrer"
            style={{ fontSize: "12px", color: "var(--color-fg-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
            <OctocatIcon /> View on GitHub
          </a>
        </div>
      </footer>

      <style>{`
        @media (max-width: 900px) {
          main > div[style*="grid-template-columns"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
