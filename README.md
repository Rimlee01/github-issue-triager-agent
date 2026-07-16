# GitHub Issue Triager Agent 

> A production-grade AI agent that automatically triages GitHub issues using LangGraph, RAG (ChromaDB), and Groq (Llama 3.3 70B). Classifies, prioritizes, detects duplicates, suggests fixes, generates PR descriptions, and drafts GitHub replies — all grounded in actual repository code.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub / User                               │
│          Webhook (new issue) ──────── Dashboard (manual)            │
└───────────────────┬─────────────────────────┬───────────────────────┘
                    │                         │
                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python 3.12)                    │
│                                                                     │
│  POST /analyze-repository ──► Celery Task ──► GitHub REST API       │
│                                    │                                │
│  WebSocket /ws/{id} ◄──────────────┤  Real-time node progress       │
│                                    │                                │
│  POST /analyze-issue ──────────────┤                                │
│                                    ▼                                │
│            ┌──────────────────────────────────────────┐             │
│            │      LangGraph Triage Workflow (7 nodes) │             │
│            │                                          │             │
│            │  1. Issue Analyzer      → summary        │             │
│            │  2. Context Retrieval   → RAG search     │◄── ChromaDB │
│            │  3. Classification      → category+labels│             │
│            │  4. Priority Assessment → priority+reason│             │
│            │  5. Solution Suggestion → fix+files      │             │
│            │  6. PR Generator        → PR description │             │
│            │  7. Response Generator  → GitHub reply   │             │
│            └──────────────────────────────────────────┘             │
│                    │                                                │
│                    ├──► PostgreSQL (analysis history, feedback)     │
│                    ├──► Redis (result caching, Celery broker)       │
│                    └──► GitHub API (auto-label, post reply)         │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                            │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐    │
│  │ Repository Panel │  │   Issue Panel    │  │ Results Panel   │    │
│  │ - URL input      │  │ - Title/desc     │  │ - Category badge│    │
│  │ - Status dot     │  │ - WS progress    │  │ - Priority badge│    │
│  │ - File/issue count│ │ - 7-node tracker │  │ - Related files │    │
│  └──────────────────┘  └──────────────────┘  │ - Solution      │    │
│                                              │ - PR description│    │
│  ┌──────────────────────────────────────────┐│ - GitHub reply  │    │
│  │ History Tab: analyses list + bar/pie     ││ - Reasoning log │    │
│  │ charts (category distribution, priority) ││ -  feedback     │    │
│  └──────────────────────────────────────────┘└─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Key architectural decisions

**LangGraph StateGraph (not a chain)** — 7 explicit nodes with typed shared state. Each node is independently testable, the reasoning trace accumulates via `operator.add`, and `MemorySaver` gives conversation-level memory across re-triages of the same issue.

**Celery + Redis for ingestion** — repo ingestion takes 30–90s (fetching 150 files + 100 issues from GitHub). Running this in a Celery worker keeps the API responsive. Flower exposes the task dashboard at `:5555`.

**PostgreSQL for persistence** — analysis history, feedback scores, and webhook events survive restarts. Async SQLAlchemy + asyncpg keeps DB access non-blocking inside FastAPI's event loop.

**Redis caching** — identical issue+repo combinations return cached results instantly (1hr TTL). Saves Groq API calls and reduces latency from ~6s to ~50ms on cache hits.

**WebSocket streaming** — the frontend connects before the analysis starts and receives real-time `node_start`/`node_complete` events per node. Falls back to simulated progress gracefully if WebSocket is unavailable.

**Per-repo ChromaDB collections** — semantic search for repo A never leaks results from repo B. `PersistentClient` survives restarts. Local `all-MiniLM-L6-v2` embeddings (384-dim) mean zero API cost for embedding 150 files.

**GitHub Webhook auto-triage** — HMAC-SHA256 signature verification on every payload, then auto-triage runs in a `BackgroundTask`. If `GITHUB_TOKEN` is set, the generated reply is posted directly back to the GitHub issue.

## Stack

| Layer | Technology |
|---|---|
| LLM | Groq — Llama 3.3 70B (free tier) |
| Agent framework | LangGraph 0.2 |
| LLM interface | LangChain + langchain-groq |
| Vector store | ChromaDB (persistent, per-repo) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (local) |
| API | FastAPI + uvicorn |
| Database | PostgreSQL 16 + asyncpg + SQLAlchemy |
| Cache/Queue | Redis 7 + Celery + Flower |
| GitHub | REST API v3 (async httpx) |
| Frontend | React 18 + Vite + Recharts |
| Styling | GitHub Primer design system (CSS variables) |
| Monitoring | Prometheus + Sentry |
| CI/CD | GitHub Actions |
| Containers | Docker + Docker Compose + Kubernetes |

## Project structure

```
github-issue-triager-agent/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph: state, prompts, 7 nodes, graph
│   │   ├── api/             # FastAPI routes + GitHub webhook handler
│   │   ├── db/              # SQLAlchemy models, async engine, CRUD
│   │   ├── github/          # Async GitHub REST API client
│   │   ├── middleware/       # API key auth
│   │   ├── models/          # Pydantic schemas (API contract)
│   │   ├── rag/             # Chunking, embeddings, ChromaDB, ingestion
│   │   ├── tasks/           # Celery app + ingestion background task
│   │   ├── tests/           # pytest unit + integration tests
│   │   ├── websocket/       # WebSocket connection manager
│   │   ├── core/            # Config (pydantic-settings), logging
│   │   └── main.py          # FastAPI app, lifespan, middleware wiring
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/          # Shared Primer-style primitives
│   │   │   ├── RepoPanel    # Repository indexing
│   │   │   ├── IssuePanel   # Issue form + real-time WS progress
│   │   │   ├── ResultsDashboard  # Full analysis output
│   │   │   ├── HistoryPanel # Past analyses list
│   │   │   └── StatsChart   # Category/priority recharts
│   │   ├── services/api.js  # All API calls + WebSocket factory
│   │   └── App.jsx          # Layout, dark/light toggle, tabs
│   ├── nginx.conf           # Security headers, gzip, WS proxy
│   └── Dockerfile           # Multi-stage build
├── k8s/                     # Kubernetes manifests
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── postgres.yaml
│   ├── redis.yaml
│   ├── backend.yaml
│   └── ingress.yaml
├── .github/
│   └── workflows/ci.yml     # Test → lint → build → push → security scan
├── docker-compose.yml       # 6 services: db, redis, backend, worker, flower, frontend
└── README.md
```

## Quick start

### Docker (recommended)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — add GROQ_API_KEY (free at console.groq.com)
cp backend/.env .env
docker compose up --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API docs | http://localhost:8001/docs |
| Metrics | http://localhost:8001/metrics |
| Flower (Celery) | http://localhost:5555 |

### Without Docker

```bash
# PostgreSQL and Redis must be running locally
cd backend
pip install -r requirements.txt
cp .env.example .env  # add GROQ_API_KEY
uvicorn app.main:app --reload --port 8001

# Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info -Q ingestion

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### Running tests

```bash
cd backend
pytest -v --cov=app
```

## API reference

### `POST /api/v1/analyze-repository`
Indexes a GitHub repository into ChromaDB (fetches files, issues, PRs).
```json
{ "repo_url": "https://github.com/owner/repo" }
```

### `POST /api/v1/analyze-issue`
Runs the 7-node LangGraph triage workflow.
```json
{
  "issue_title": "App crashes on large file upload",
  "issue_description": "Server returns 500 on files > 50MB...",
  "repo_id": "owner__repo"
}
```
Returns: summary, category, priority, related_files, similar_issues, duplicate detection, solution, PR description, GitHub reply, reasoning_trace, processing_time_ms.

### `WebSocket /api/v1/ws/{analysis_id}`
Connect before calling `/analyze-issue` to receive real-time node progress events.

### `GET /api/v1/repositories/{repo_id}/history`
Returns all past analyses for a repository.

### `POST /api/v1/analyses/{analysis_id}/feedback?score=1`
Submit thumbs up (1) or thumbs down (-1) feedback.

### `POST /api/v1/analyses/{analysis_id}/apply-labels`
Applies suggested labels directly to the GitHub issue via API.

### `POST /api/v1/webhooks/github`
GitHub webhook receiver (HMAC-SHA256 verified). Configure in repo Settings → Webhooks.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Free at console.groq.com |
| `GITHUB_TOKEN` | Recommended | Raises rate limit 60→5000 req/hr |
| `GITHUB_WEBHOOK_SECRET` | For webhooks | Any random secret string |
| `ENABLE_AUTH` | Production | Set `true` to require `X-API-Key` header |
| `API_KEY` | Production | Key value when auth is enabled |
| `SENTRY_DSN` | Optional | Error tracking |
| `RATE_LIMIT_PER_MINUTE` | Optional | Default: 30 |

## Advanced features

- **Duplicate detection**: cosine similarity against past issues, flagged above 0.85 threshold
- **Confidence scores**: per-field confidence with visual progress bars
- **Confidence explanation**: `chunk_influence` field shows which retrieved chunks drove each decision
- **Auto-labeling**: `POST /apply-labels` pushes labels to the real GitHub issue
- **PR description generation**: node 6 produces a ready-to-use PR description
- **Feedback loop**: thumbs up/down stored in PostgreSQL for future fine-tuning data
- **Result caching**: Redis caches identical issue analyses (1hr TTL)
- **Dark/light mode**: respects system preference, toggleable in header
- **Mobile responsive**: single-column layout below 900px
- **Onboarding flow**: step-by-step banner for first-time users

## Author

**RimLee Deka** — AI Engineer | Python Developer | Full Stack Developer
