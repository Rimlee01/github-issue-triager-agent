"""
Ingestion pipeline: GitHub fetch -> chunk -> embed -> store in ChromaDB.

This is the orchestration layer that Phase 1 (GitHub client) and
Phase 2 (chunking/vectorstore) compose around. Kept separate from the
FastAPI route handler so it's independently testable/reusable (e.g. from
a CLI script or background worker).
"""
from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.github.client import GitHubClient, RepoIdentity, parse_repo_url
from app.models.schemas import RepositoryStatus
from app.rag.embeddings import chunk_file, chunk_issue, chunk_readme
from app.rag.registry import RepoRecord, get_repo_registry
from app.rag.vectorstore import RepoVectorStore

logger = get_logger(__name__)


def make_repo_id(repo: RepoIdentity) -> str:
    return f"{repo.owner}__{repo.name}"


async def ingest_repository(repo_url: str) -> RepoRecord:
    """End-to-end ingestion: fetch repo data from GitHub, chunk it, embed it,
    store it in a per-repo ChromaDB collection, and register it for later
    issue-analysis lookups.
    """
    registry = get_repo_registry()
    repo_identity = parse_repo_url(repo_url)
    repo_id = make_repo_id(repo_identity)

    record = RepoRecord(
        repo_id=repo_id,
        owner=repo_identity.owner,
        name=repo_identity.name,
        default_branch="main",
        status=RepositoryStatus.INGESTING,
    )
    registry.upsert(record)

    client = GitHubClient()
    try:
        metadata = await client.get_repo_metadata(repo_identity)
        record.default_branch = metadata["default_branch"]
        record.description = metadata.get("description")

        readme, files, issues, prs = await asyncio.gather(
            client.get_readme(repo_identity),
            client.fetch_source_files(repo_identity, record.default_branch),
            client.fetch_issues(repo_identity, state="all"),
            client.fetch_pull_requests(repo_identity, state="all"),
        )

        store = RepoVectorStore(repo_id)
        store.reset()  # fresh ingestion replaces any prior index for this repo

        all_chunks = []
        if readme:
            all_chunks.extend(chunk_readme(repo_id, readme))
        for f in files:
            all_chunks.extend(chunk_file(f, repo_id))
        for issue in issues:
            all_chunks.append(
                chunk_issue(repo_id, issue.number, issue.title, issue.body, issue.url, issue.labels)
            )

        store.add_chunks(all_chunks)

        record.files_ingested = len(files)
        record.issues_ingested = len(issues)
        record.pull_requests_ingested = len(prs)
        record.issues = issues
        record.status = RepositoryStatus.READY

        logger.info(
            "repository_ingested",
            repo_id=repo_id,
            files=len(files),
            issues=len(issues),
            prs=len(prs),
            chunks=len(all_chunks),
        )

    except Exception as exc:
        logger.error("repository_ingestion_failed", repo_id=repo_id, error=str(exc))
        record.status = RepositoryStatus.FAILED
        record.error = str(exc)
        raise
    finally:
        registry.upsert(record)
        await client.close()

    return record
