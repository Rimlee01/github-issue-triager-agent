const BASE = import.meta.env.VITE_API_URL || "/api/v1";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  analyzeRepository: (repoUrl) =>
    request("/analyze-repository", { method: "POST", body: JSON.stringify({ repo_url: repoUrl }) }),

  analyzeIssue: ({ issueTitle, issueDescription, repoId, analysisId }) =>
    request("/analyze-issue", {
      method: "POST",
      body: JSON.stringify({
        issue_title: issueTitle,
        issue_description: issueDescription,
        repo_id: repoId,
        analysis_id: analysisId,
      }),
    }),

  listRepositories: () => request("/repositories"),
  getHistory: (repoId) => request(`/repositories/${repoId}/history`),

  submitFeedback: (analysisId, score, comment = "") =>
    request(`/analyses/${analysisId}/feedback?score=${score}&comment=${encodeURIComponent(comment)}`, { method: "POST" }),
};

export function createSSE(analysisId, onEvent) {
  const es = new EventSource(`${BASE}/progress/${analysisId}`);
  es.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)); } catch {}
  };
  es.onerror = () => es.close();
  return es;
}
