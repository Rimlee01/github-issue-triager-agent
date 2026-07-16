"""Unit tests for agent nodes — test logic without real LLM or vector store."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_issue_analyzer_node():
    from app.agents.nodes import issue_analyzer_node
    with patch("app.agents.nodes.call_llm_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {
            "summary": "App crashes on large file upload",
            "technical_area": "file upload handling",
        }
        state = {
            "issue_title": "App crashes when uploading large files",
            "issue_description": "500 error on files > 50MB",
            "analysis_id": "",
        }
        result = await issue_analyzer_node(state)
        assert result["summary"] == "App crashes on large file upload"
        assert result["technical_area"] == "file upload handling"
        assert len(result["reasoning_trace"]) == 1


@pytest.mark.asyncio
async def test_classification_node():
    from app.agents.nodes import classification_node
    with patch("app.agents.nodes.call_llm_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {
            "category": "bug",
            "category_confidence": 0.92,
            "suggested_labels": ["bug", "upload"],
        }
        state = {
            "summary": "App crashes",
            "technical_area": "upload",
            "issue_title": "Upload crash",
            "issue_description": "crashes on big files",
            "related_files": [],
            "analysis_id": "",
        }
        result = await classification_node(state)
        assert result["category"] == "bug"
        assert result["category_confidence"] == 0.92
        assert "bug" in result["suggested_labels"]


@pytest.mark.asyncio
async def test_priority_assessment_node():
    from app.agents.nodes import priority_assessment_node
    with patch("app.agents.nodes.call_llm_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {
            "priority": "high",
            "priority_reason": "Core functionality broken with no workaround",
        }
        state = {
            "summary": "App crashes",
            "category": "bug",
            "technical_area": "upload",
            "issue_description": "crashes on big files",
            "similar_issues": [],
            "analysis_id": "",
        }
        result = await priority_assessment_node(state)
        assert result["priority"] == "high"
        assert "workaround" in result["priority_reason"]


@pytest.mark.asyncio
async def test_repo_context_retrieval_no_duplicates():
    from app.agents.nodes import repo_context_retrieval_node
    mock_store = MagicMock()
    mock_store.query.return_value = [
        {"text": "def upload(f): write(f)", "metadata": {"file_path": "storage.py"}, "similarity": 0.8}
    ]
    with patch("app.agents.nodes.RepoVectorStore", return_value=mock_store):
        state = {
            "repo_id": "owner__repo",
            "issue_title": "Upload bug",
            "issue_description": "crashes",
            "summary": "upload crashes",
            "analysis_id": "",
        }
        result = await repo_context_retrieval_node(state)
        assert isinstance(result["related_files"], list)
        assert isinstance(result["similar_issues"], list)
        assert result["duplicate_of"] is None
