"""
Database CRUD operations.

Keeping DB operations in a dedicated module (not scattered in routes)
makes them independently testable and reusable across routes and tasks.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IssueAnalysis, Repository, WebhookEvent


# ── Repository ──────────────────────────────────────────────────

async def get_repository(db: AsyncSession, repo_id: str) -> Optional[Repository]:
    result = await db.execute(select(Repository).where(Repository.repo_id == repo_id))
    return result.scalar_one_or_none()


async def upsert_repository(db: AsyncSession, **kwargs) -> Repository:
    repo = await get_repository(db, kwargs["repo_id"])
    if repo:
        for k, v in kwargs.items():
            setattr(repo, k, v)
        repo.updated_at = datetime.utcnow()
    else:
        repo = Repository(**kwargs)
        db.add(repo)
    await db.flush()
    return repo


async def list_repositories(db: AsyncSession) -> list[Repository]:
    result = await db.execute(select(Repository).order_by(desc(Repository.created_at)))
    return list(result.scalars().all())


# ── Issue Analysis ───────────────────────────────────────────────

async def create_analysis(db: AsyncSession, **kwargs) -> IssueAnalysis:
    analysis = IssueAnalysis(id=uuid.uuid4(), **kwargs)
    db.add(analysis)
    await db.flush()
    return analysis


async def update_analysis_feedback(
    db: AsyncSession, analysis_id: str, score: int, comment: Optional[str] = None
) -> Optional[IssueAnalysis]:
    result = await db.execute(
        select(IssueAnalysis).where(IssueAnalysis.id == uuid.UUID(analysis_id))
    )
    analysis = result.scalar_one_or_none()
    if analysis:
        analysis.feedback_score = score
        analysis.feedback_comment = comment
        await db.flush()
    return analysis


async def list_analyses(db: AsyncSession, repo_id: str, limit: int = 50) -> list[IssueAnalysis]:
    result = await db.execute(
        select(IssueAnalysis)
        .where(IssueAnalysis.repo_id == repo_id)
        .order_by(desc(IssueAnalysis.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_analysis_by_cache_key(
    db: AsyncSession, repo_id: str, issue_title: str, issue_description: str
) -> Optional[IssueAnalysis]:
    """Check if we already analyzed this exact issue before (cache hit)."""
    result = await db.execute(
        select(IssueAnalysis)
        .where(
            IssueAnalysis.repo_id == repo_id,
            IssueAnalysis.issue_title == issue_title,
            IssueAnalysis.issue_description == issue_description,
        )
        .order_by(desc(IssueAnalysis.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── Webhook Events ───────────────────────────────────────────────

async def create_webhook_event(db: AsyncSession, **kwargs) -> WebhookEvent:
    event = WebhookEvent(id=uuid.uuid4(), **kwargs)
    db.add(event)
    await db.flush()
    return event


async def update_webhook_event(db: AsyncSession, event_id, **kwargs) -> None:
    result = await db.execute(select(WebhookEvent).where(WebhookEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event:
        for k, v in kwargs.items():
            setattr(event, k, v)
        await db.flush()
