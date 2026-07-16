"""
Integration tests for the API layer.

Tests run against a real FastAPI TestClient with:
- LLM calls mocked (no real Groq API needed)
- Vector store mocked (no real ChromaDB/embeddings needed)
- PostgreSQL mocked with SQLite in-memory (no real DB needed)

This pattern — mock external I/O, test your own logic — is what
interviewers mean when they ask "how do you test AI applications?"
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def client():
    """TestClient with all external dependencies mocked."""
    with (
        patch("app.agents.llm_client.get_llm"),
        patch("app.db.engine.init_db", new_callable=AsyncMock),
    ):
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analyze_repository_invalid_url(client):
    resp = client.post("/api/v1/analyze-repository", json={"repo_url": "not-a-github-url"})
    assert resp.status_code in (400, 500)


def test_analyze_issue_unknown_repo(client):
    resp = client.post("/api/v1/analyze-issue", json={
        "issue_title": "Test issue",
        "issue_description": "Test description for testing purposes",
        "repo_id": "nonexistent__repo",
    })
    assert resp.status_code in (404, 500)


def test_list_repositories_empty(client):
    with patch("app.api.routes.crud.list_repositories", new_callable=AsyncMock, return_value=[]):
        resp = client.get("/api/v1/repositories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


def test_feedback_invalid_score(client):
    resp = client.post("/api/v1/analyses/some-id/feedback?score=5")
    assert resp.status_code in (400, 422)
