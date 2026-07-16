"""
LangGraph agent nodes — upgraded to use SSE instead of WebSocket for progress streaming.
"""
from __future__ import annotations

from app.agents.llm_client import call_llm_json, call_llm_text
from app.agents.prompts import (
    CLASSIFICATION_PROMPT,
    ISSUE_ANALYZER_PROMPT,
    PR_DESCRIPTION_PROMPT,
    PRIORITY_PROMPT,
    RESPONSE_GENERATOR_PROMPT,
    SOLUTION_PROMPT,
)
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.vectorstore import RepoVectorStore

logger = get_logger(__name__)
settings = get_settings()


async def _emit_start(analysis_id: str, node: str, index: int):
    if not analysis_id:
        return
    try:
        from app.api.sse import push_event
        await push_event(analysis_id, {"type": "node_start", "node": node, "index": index, "total": 7})
    except Exception:
        pass


async def _emit_complete(analysis_id: str, node: str, index: int, summary: str):
    if not analysis_id:
        return
    try:
        from app.api.sse import push_event
        await push_event(analysis_id, {"type": "node_complete", "node": node, "index": index, "summary": summary})
    except Exception:
        pass


# ── Node 1: Issue Analyzer ──────────────────────────────────────

async def issue_analyzer_node(state: AgentState) -> dict:
    aid = state.get("analysis_id", "")
    await _emit_start(aid, "Issue Analyzer", 0)
    prompt = ISSUE_ANALYZER_PROMPT.format(
        issue_title=state["issue_title"],
        issue_description=state["issue_description"],
    )
    result = await call_llm_json(prompt)
    summary = result.get("summary", "")
    technical_area = result.get("technical_area", "unknown")
    await _emit_complete(aid, "Issue Analyzer", 0, f"Technical area: {technical_area}")
    return {
        "summary": summary,
        "technical_area": technical_area,
        "reasoning_trace": [f"[Issue Analyzer] Summary: \"{summary}\" — area: {technical_area}"],
    }


# ── Node 2: Repository Context Retrieval ───────────────────────

def _format_files_context(files: list[dict]) -> str:
    if not files:
        return "(no relevant code found)"
    return "\n\n".join(
        f"--- {f['path']} (relevance {f['relevance_score']:.2f}) ---\n{f['snippet']}"
        for f in files
    )


def _format_issues_context(issues: list[dict]) -> str:
    if not issues:
        return "(no similar issues found)"
    return "\n".join(
        f"#{i.get('number','?')} \"{i['title']}\" (similarity {i['similarity_score']:.2f})"
        for i in issues
    )


async def repo_context_retrieval_node(state: AgentState) -> dict:
    aid = state.get("analysis_id", "")
    await _emit_start(aid, "Repository Context", 1)
    repo_id = state["repo_id"]
    query = f"{state['issue_title']}\n{state.get('summary','')}\n{state['issue_description']}"
    store = RepoVectorStore(repo_id)
    code_results = store.query(query, top_k=settings.RAG_TOP_K, source_type="code")
    readme_results = store.query(query, top_k=2, source_type="readme")
    issue_results = store.query(query, top_k=settings.RAG_TOP_K, source_type="issue")
    related_files = [
        {"path": r["metadata"].get("file_path", "unknown"), "relevance_score": r["similarity"],
         "snippet": r["text"][:500], "chunk_influence": f"similarity={r['similarity']:.3f}"}
        for r in (code_results + readme_results)
    ]
    similar_issues = [
        {"number": r["metadata"].get("issue_number"), "title": r["metadata"].get("title", ""),
         "similarity_score": r["similarity"], "url": r["metadata"].get("url"),
         "is_likely_duplicate": r["similarity"] >= settings.DUPLICATE_SIMILARITY_THRESHOLD}
        for r in issue_results
    ]
    similar_issues.sort(key=lambda x: x["similarity_score"], reverse=True)
    duplicate_of = next((i for i in similar_issues if i["is_likely_duplicate"]), None)
    summary = f"Found {len(related_files)} files, {len(similar_issues)} similar issues"
    await _emit_complete(aid, "Repository Context", 1, summary)
    return {
        "related_files": related_files, "similar_issues": similar_issues,
        "duplicate_of": duplicate_of,
        "reasoning_trace": [f"[Repo Context] {summary}"],
    }


# ── Node 3: Classification ──────────────────────────────────────

async def classification_node(state: AgentState) -> dict:
    aid = state.get("analysis_id", "")
    await _emit_start(aid, "Classification", 2)
    prompt = CLASSIFICATION_PROMPT.format(
        summary=state.get("summary", ""), technical_area=state.get("technical_area", ""),
        issue_title=state["issue_title"], issue_description=state["issue_description"],
        repo_context=_format_files_context(state.get("related_files", [])),
    )
    result = await call_llm_json(prompt)
    category = result.get("category", "unknown")
    confidence = float(result.get("category_confidence", 0.5))
    labels = result.get("suggested_labels", [])
    await _emit_complete(aid, "Classification", 2, f"{category} ({confidence:.0%} confidence)")
    return {
        "category": category, "category_confidence": confidence, "suggested_labels": labels,
        "reasoning_trace": [f"[Classification] {category} ({confidence:.0%}), labels: {labels}"],
    }


# ── Node 4: Priority Assessment ─────────────────────────────────

async def priority_assessment_node(state: AgentState) -> dict:
    aid = state.get("analysis_id", "")
    await _emit_start(aid, "Priority Assessment", 3)
    prompt = PRIORITY_PROMPT.format(
        summary=state.get("summary", ""), category=state.get("category", ""),
        technical_area=state.get("technical_area", ""), issue_description=state["issue_description"],
        similar_issues_context=_format_issues_context(state.get("similar_issues", [])),
    )
    result = await call_llm_json(prompt)
    priority = result.get("priority", "medium")
    reason = result.get("priority_reason", "")
    await _emit_complete(aid, "Priority Assessment", 3, f"Priority: {priority}")
    return {
        "priority": priority, "priority_reason": reason,
        "reasoning_trace": [f"[Priority] {priority} — {reason}"],
    }


# ── Node 5: Solution Suggestion ─────────────────────────────────

async def solution_suggestion_node(state: AgentState) -> dict:
    aid = state.get("analysis_id", "")
    await _emit_start(aid, "Solution Suggestion", 4)
    prompt = SOLUTION_PROMPT.format(
        summary=state.get("summary", ""), category=state.get("category", ""),
        technical_area=state.get("technical_area", ""), issue_description=state["issue_description"],
        repo_context=_format_files_context(state.get("related_files", [])),
    )
    result = await call_llm_json(prompt)
    confidence = float(result.get("solution_confidence", 0.5))
    await _emit_complete(aid, "Solution Suggestion", 4, f"Root cause identified ({confidence:.0%} confidence)")
    return {
        "root_cause": result.get("root_cause", ""), "suggested_fix": result.get("suggested_fix", ""),
        "files_to_modify": result.get("files_to_modify", []),
        "implementation_approach": result.get("implementation_approach", ""),
        "solution_confidence": confidence,
        "reasoning_trace": [f"[Solution] {result.get('root_cause','')[:100]} ({confidence:.0%})"],
    }


# ── Node 6: PR Description ───────────────────────────────────────

async def pr_description_node(state: AgentState) -> dict:
    aid = state.get("analysis_id", "")
    await _emit_start(aid, "PR Description", 5)
    prompt = PR_DESCRIPTION_PROMPT.format(
        summary=state.get("summary", ""), root_cause=state.get("root_cause", ""),
        suggested_fix=state.get("suggested_fix", ""),
        files_to_modify=", ".join(state.get("files_to_modify", [])),
        implementation_approach=state.get("implementation_approach", ""),
    )
    pr_description = await call_llm_text(prompt)
    await _emit_complete(aid, "PR Description", 5, "PR description drafted")
    return {
        "pr_description": pr_description.strip(),
        "reasoning_trace": ["[PR Description] Generated pull request description"],
    }


# ── Node 7: Response Generator ───────────────────────────────────

async def response_generator_node(state: AgentState) -> dict:
    aid = state.get("analysis_id", "")
    await _emit_start(aid, "Response Generator", 6)
    duplicate = state.get("duplicate_of")
    duplicate_info = (
        f"Yes — likely duplicate of issue #{duplicate['number']}: \"{duplicate['title']}\""
        if duplicate else "No duplicate detected"
    )
    prompt = RESPONSE_GENERATOR_PROMPT.format(
        summary=state.get("summary", ""), category=state.get("category", ""),
        priority=state.get("priority", ""), root_cause=state.get("root_cause", ""),
        suggested_fix=state.get("suggested_fix", ""),
        implementation_approach=state.get("implementation_approach", ""),
        duplicate_info=duplicate_info,
    )
    generated_response = await call_llm_text(prompt)
    await _emit_complete(aid, "Response Generator", 6, "GitHub reply drafted")
    return {
        "generated_response": generated_response.strip(),
        "reasoning_trace": ["[Response Generator] Drafted GitHub-style reply"],
    }
