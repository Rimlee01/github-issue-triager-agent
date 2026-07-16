"""
In-memory repository registry.

Decision: for a portfolio-scale project we avoid standing up Postgres just
to store {repo_id -> metadata}. An in-memory dict keyed by repo_id is
sufficient and keeps the deployment story simple (no DB migrations).
The interface is deliberately narrow (a small class, not module-level
globals scattered everywhere) so swapping in a real DB later is a
single-file change — implement the same methods against SQLAlchemy/Postgres.
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.schemas import GitHubIssueRecord, RepositoryStatus


class RepoRecord(BaseModel):
    repo_id: str
    owner: str
    name: str
    default_branch: str
    description: Optional[str] = None
    status: RepositoryStatus = RepositoryStatus.PENDING
    files_ingested: int = 0
    issues_ingested: int = 0
    pull_requests_ingested: int = 0
    issues: list[GitHubIssueRecord] = []
    error: Optional[str] = None
    created_at: datetime = datetime.utcnow()


class RepoRegistry:
    """Thread-safe in-memory store of ingested repositories."""

    def __init__(self):
        self._repos: dict[str, RepoRecord] = {}
        self._lock = threading.Lock()

    def upsert(self, record: RepoRecord) -> None:
        with self._lock:
            self._repos[record.repo_id] = record

    def get(self, repo_id: str) -> RepoRecord | None:
        with self._lock:
            return self._repos.get(repo_id)

    def exists(self, repo_id: str) -> bool:
        with self._lock:
            return repo_id in self._repos

    def list_all(self) -> list[RepoRecord]:
        with self._lock:
            return list(self._repos.values())


_registry = RepoRegistry()


def get_repo_registry() -> RepoRegistry:
    return _registry
