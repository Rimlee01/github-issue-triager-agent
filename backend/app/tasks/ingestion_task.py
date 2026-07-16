"""
Celery task for async repository ingestion.

Runs in a separate worker process so the API stays responsive while
fetching 150 files + 100 issues from GitHub (which can take 30-90s).
"""
from __future__ import annotations

import asyncio

from app.tasks.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="app.tasks.ingestion_task.ingest_repository_task",
)
def ingest_repository_task(self, repo_url: str, repo_id: str):
    """
    Background task: fetch repo from GitHub, chunk, embed, store in ChromaDB.
    Updates PostgreSQL status as it progresses.
    """
    try:
        asyncio.run(_async_ingest(repo_url, repo_id))
    except Exception as exc:
        logger.error("ingestion_task_failed", repo_id=repo_id, error=str(exc))
        raise self.retry(exc=exc)


async def _async_ingest(repo_url: str, repo_id: str):
    """Async ingestion logic wrapped for Celery's sync task interface."""
    from app.rag.ingestion import ingest_repository
    from app.db.engine import get_session_factory
    from app.db import crud

    async with get_session_factory()() as db:
        try:
            await crud.upsert_repository(db, repo_id=repo_id, status="ingesting",
                                          owner="", name="", full_name=repo_id)
            await db.commit()

            record = await ingest_repository(repo_url)

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
            await db.commit()
            logger.info("ingestion_task_complete", repo_id=repo_id)

        except Exception as exc:
            await crud.upsert_repository(db, repo_id=repo_id, status="failed",
                                          owner="", name="", full_name=repo_id, error=str(exc))
            await db.commit()
            raise
