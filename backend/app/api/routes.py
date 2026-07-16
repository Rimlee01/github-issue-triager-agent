"""
API routes — upgraded with:
- PostgreSQL persistence
- Redis caching for analysis results
- Feedback endpoint
- Analysis history endpoint
- Auto-label application to GitHub
- SSE endpoint for real-time streaming
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_triage
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import crud
from app.db.engine import get_db
from app.github.client import GitHubAPIError
from app.middleware.auth import verify_api_key
from app.models.schemas import (
    AnalyzeIssueRequest,
    AnalyzeIssueResponse,
    AnalyzeRepositoryRequest,
    AnalyzeRepositoryResponse,
    IssueCategory,
    IssuePriority,
    RelatedFile,
    RepositoryStatus,
    SimilarIssue,
    SolutionSuggestion,
)
from app.rag.ingestion import ingest_repository
from app.rag.registry import get_repo_registry

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter()


# ── Redis cache helper ───────────────────────────────────────────

def _cache_key(repo_id: str, title: str, description: str) -> str:
    raw = f"{repo_id}:{title}:{description}"
    return "analysis:" + hashlib.sha256(raw.encode()).hexdigest()


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


# ── Repository endpoints ─────────────────────────────────────────

@router.post("/analyze-repository", response_model=AnalyzeRepositoryResponse,
             dependencies=[Depends(verify_api_key)])
async def analyze_repository(
    req: AnalyzeRepositoryRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        record = await ingest_repository(req.repo_url)
    except GitHubAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("analyze_repository_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    await crud.upsert_repository(
        db,
        repo_id=record.repo_id,
        owner=record.owner,
        name=record.name,
        full_name=f"{record.owner}/{record.name}",
        default_branch=record.default_branch,
        description=record.description,
        status=record.status.value,
        files_ingested=record.files_ingested,
        issues_ingested=record.issues_ingested,
        pull_requests_ingested=record.pull_requests_ingested,
    )

    return AnalyzeRepositoryResponse(
        repo_id=record.repo_id,
        owner=record.owner,
        name=record.name,
        status=record.status,
        files_ingested=record.files_ingested,
        issues_ingested=record.issues_ingested,
        pull_requests_ingested=record.pull_requests_ingested,
        message=f"Indexed {record.files_ingested} files, {record.issues_ingested} issues.",
    )


@router.get("/repositories", dependencies=[Depends(verify_api_key)])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    repos = await crud.list_repositories(db)
    registry = get_repo_registry()
    result = []
    for r in repos:
        mem = registry.get(r.repo_id)
        result.append({
            "repo_id": r.repo_id,
            "owner": r.owner,
            "name": r.name,
            "status": mem.status.value if mem else r.status,
            "files_ingested": r.files_ingested,
            "issues_ingested": r.issues_ingested,
            "created_at": r.created_at.isoformat(),
        })
    return result


# ── Issue analysis endpoints ─────────────────────────────────────

@router.post("/analyze-issue", response_model=AnalyzeIssueResponse,
             dependencies=[Depends(verify_api_key)])
async def analyze_issue(
    req: AnalyzeIssueRequest,
    db: AsyncSession = Depends(get_db),
):
    registry = get_repo_registry()
    record = registry.get(req.repo_id)
    if not record:
        db_repo = await crud.get_repository(db, req.repo_id)
        if not db_repo:
            raise HTTPException(status_code=404, detail=f"Unknown repo_id '{req.repo_id}'.")
    if record and record.status != RepositoryStatus.READY:
        raise HTTPException(status_code=409, detail=f"Repository not ready (status: {record.status}).")

    # Check Redis cache — skip cache if analysis_id provided (live triage with animation)
    redis = await _get_redis()
    cache_key = _cache_key(req.repo_id, req.issue_title, req.issue_description)
    if not req.analysis_id:
        cached = await redis.get(cache_key)
        if cached:
            logger.info("cache_hit", repo_id=req.repo_id)
            return AnalyzeIssueResponse(**json.loads(cached))

    issue_id = req.analysis_id or str(uuid.uuid4())
    start_time = time.time()

    # Give SSE connection time to be established before first event
    if req.analysis_id:
        await asyncio.sleep(0.3)

    try:
        final_state = await run_triage(
            repo_id=req.repo_id,
            issue_title=req.issue_title,
            issue_description=req.issue_description,
            thread_id=issue_id,
            analysis_id=issue_id,
        )
    except Exception as exc:
        logger.error("analyze_issue_failed", repo_id=req.repo_id, error=str(exc))
        if req.analysis_id:
            from app.api.sse import push_event
            await push_event(issue_id, {"type": "error", "message": str(exc)})
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    processing_time = int((time.time() - start_time) * 1000)

    # Signal SSE stream that we're done
    if req.analysis_id:
        from app.api.sse import push_event
        await push_event(issue_id, {"type": "done"})

    duplicate_raw = final_state.get("duplicate_of")
    duplicate_of = SimilarIssue(**duplicate_raw) if duplicate_raw else None

    response = AnalyzeIssueResponse(
        issue_id=issue_id,
        summary=final_state.get("summary", ""),
        category=IssueCategory(final_state.get("category", "unknown").lower()),
        category_confidence=final_state.get("category_confidence", 0.0),
        priority=IssuePriority(final_state.get("priority", "medium").lower()),
        priority_reason=final_state.get("priority_reason", ""),
        technical_area=final_state.get("technical_area", ""),
        suggested_labels=final_state.get("suggested_labels", []),
        related_files=[RelatedFile(**f) for f in final_state.get("related_files", [])],
        similar_issues=[SimilarIssue(**i) for i in final_state.get("similar_issues", [])],
        duplicate_of=duplicate_of,
        suggested_solution=SolutionSuggestion(
            root_cause=final_state.get("root_cause", ""),
            suggested_fix=final_state.get("suggested_fix", ""),
            files_to_modify=final_state.get("files_to_modify", []),
            implementation_approach=final_state.get("implementation_approach", ""),
            confidence_score=final_state.get("solution_confidence", 0.0),
        ),
        pr_description=final_state.get("pr_description", ""),
        generated_response=final_state.get("generated_response", ""),
        reasoning_trace=final_state.get("reasoning_trace", []),
        processing_time_ms=processing_time,
    )

    # Persist to PostgreSQL
    await crud.create_analysis(
        db,
        repo_id=req.repo_id,
        issue_title=req.issue_title,
        issue_description=req.issue_description,
        summary=response.summary,
        category=response.category.value,
        category_confidence=response.category_confidence,
        priority=response.priority.value,
        priority_reason=response.priority_reason,
        technical_area=response.technical_area,
        suggested_labels=response.suggested_labels,
        related_files=[f.model_dump() for f in response.related_files],
        similar_issues=[i.model_dump() for i in response.similar_issues],
        duplicate_of=response.duplicate_of.model_dump() if response.duplicate_of else None,
        root_cause=response.suggested_solution.root_cause,
        suggested_fix=response.suggested_solution.suggested_fix,
        files_to_modify=response.suggested_solution.files_to_modify,
        implementation_approach=response.suggested_solution.implementation_approach,
        solution_confidence=response.suggested_solution.confidence_score,
        pr_description=response.pr_description,
        generated_response=response.generated_response,
        reasoning_trace=response.reasoning_trace,
        processing_time_ms=processing_time,
    )

    # Cache in Redis
    await redis.setex(cache_key, settings.CACHE_TTL_SECONDS, response.model_dump_json())

    return response


@router.get("/repositories/{repo_id}/history", dependencies=[Depends(verify_api_key)])
async def get_analysis_history(repo_id: str, db: AsyncSession = Depends(get_db)):
    analyses = await crud.list_analyses(db, repo_id)
    return [
        {
            "issue_id": str(a.id),
            "issue_title": a.issue_title,
            "category": a.category,
            "priority": a.priority,
            "category_confidence": a.category_confidence,
            "feedback_score": a.feedback_score,
            "processing_time_ms": a.processing_time_ms,
            "created_at": a.created_at.isoformat(),
        }
        for a in analyses
    ]


@router.post("/analyses/{analysis_id}/feedback", dependencies=[Depends(verify_api_key)])
async def submit_feedback(
    analysis_id: str,
    score: int,
    comment: str = "",
    db: AsyncSession = Depends(get_db),
):
    if score not in (1, -1):
        raise HTTPException(status_code=400, detail="Score must be 1 (positive) or -1 (negative).")
    result = await crud.update_analysis_feedback(db, analysis_id, score, comment)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return {"status": "ok", "analysis_id": analysis_id, "score": score}


@router.post("/analyses/{analysis_id}/apply-labels", dependencies=[Depends(verify_api_key)])
async def apply_labels_to_github(
    analysis_id: str,
    repo_id: str,
    issue_number: int,
    db: AsyncSession = Depends(get_db),
):
    """Apply suggested labels directly to the real GitHub issue via API."""
    import httpx
    from app.db.models import IssueAnalysis
    import uuid as _uuid
    from sqlalchemy import select
    r = await db.execute(
        select(IssueAnalysis).where(IssueAnalysis.id == _uuid.UUID(analysis_id))
    )
    analysis = r.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    if not settings.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN not configured.")

    owner, name = repo_id.split("__", 1)
    url = f"https://api.github.com/repos/{owner}/{name}/issues/{issue_number}/labels"
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"labels": analysis.suggested_labels}, headers=headers)
        resp.raise_for_status()

    return {"status": "ok", "labels_applied": analysis.suggested_labels}