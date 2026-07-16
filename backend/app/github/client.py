"""
Async GitHub REST API client.

Decision: we hand-roll a thin async client over httpx rather than using
PyGithub (which is sync-only and would block the FastAPI event loop under
concurrent requests). This keeps ingestion fully async and lets us fetch
file trees, issues, and PRs concurrently with asyncio.gather.
"""
from __future__ import annotations

import asyncio
import base64
import re
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import GitHubIssueRecord, IngestedFile

logger = get_logger(__name__)
settings = get_settings()


class GitHubAPIError(Exception):
    """Raised for unrecoverable GitHub API failures (bad URL, 404, auth)."""


class GitHubRateLimitError(Exception):
    """Raised when GitHub's rate limit is exhausted."""


@dataclass
class RepoIdentity:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


def parse_repo_url(repo_url: str) -> RepoIdentity:
    """Extracts owner/repo from a variety of GitHub URL formats."""
    repo_url = repo_url.strip().rstrip("/")
    match = re.search(r"github\.com[/:]([^/]+)/([^/.]+?)(?:\.git)?$", repo_url)
    if not match:
        raise GitHubAPIError(f"Could not parse a valid GitHub repo URL from: {repo_url}")
    return RepoIdentity(owner=match.group(1), name=match.group(2))


class GitHubClient:
    """Thin async wrapper around the GitHub REST API."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self._client = httpx.AsyncClient(
            base_url=settings.GITHUB_API_BASE,
            headers=headers,
            timeout=30.0,
            follow_redirects=True,  # GitHub 301s on renamed repos (e.g. tiangolo/fastapi -> fastapi/fastapi)
        )

    async def close(self):
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(httpx.TransportError),
    )
    async def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        resp = await self._client.get(path, params=params)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise GitHubRateLimitError("GitHub API rate limit exceeded. Add a GITHUB_TOKEN to increase it.")
        if resp.status_code == 404:
            raise GitHubAPIError(f"GitHub resource not found: {path}")
        if resp.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error {resp.status_code} for {path}: {resp.text[:200]}")
        return resp

    # ───────────────────────── Repository metadata ─────────────────────────

    async def get_repo_metadata(self, repo: RepoIdentity) -> dict:
        resp = await self._get(f"/repos/{repo.full_name}")
        data = resp.json()
        return {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "default_branch": data.get("default_branch", "main"),
            "language": data.get("language"),
            "stars": data.get("stargazers_count"),
            "open_issues_count": data.get("open_issues_count"),
            "topics": data.get("topics", []),
        }

    async def get_readme(self, repo: RepoIdentity) -> str:
        try:
            resp = await self._get(f"/repos/{repo.full_name}/readme")
            data = resp.json()
            content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            return content
        except GitHubAPIError:
            logger.warning("no_readme_found", repo=repo.full_name)
            return ""

    # ───────────────────────── Source files ─────────────────────────

    async def get_file_tree(self, repo: RepoIdentity, branch: str) -> list[dict]:
        resp = await self._get(
            f"/repos/{repo.full_name}/git/trees/{branch}",
            params={"recursive": "1"},
        )
        tree = resp.json().get("tree", [])
        return [item for item in tree if item.get("type") == "blob"]

    async def get_file_content(self, repo: RepoIdentity, path: str) -> str | None:
        try:
            resp = await self._get(f"/repos/{repo.full_name}/contents/{path}")
            data = resp.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            return None
        except (GitHubAPIError, UnicodeDecodeError):
            return None

    async def fetch_source_files(
        self, repo: RepoIdentity, branch: str
    ) -> list[IngestedFile]:
        """Fetches relevant source files from the repo, respecting size/count caps."""
        tree = await self.get_file_tree(repo, branch)

        candidates = [
            item for item in tree
            if any(item["path"].endswith(ext) for ext in settings.ALLOWED_CODE_EXTENSIONS)
            and item.get("size", 0) <= settings.MAX_FILE_SIZE_BYTES
            and "node_modules" not in item["path"]
            and not item["path"].startswith(".")
        ][: settings.MAX_FILES_TO_INGEST]

        logger.info("fetching_source_files", repo=repo.full_name, count=len(candidates))

        # Fetch concurrently but bound concurrency to avoid hammering the API
        semaphore = asyncio.Semaphore(10)

        async def fetch_one(item: dict) -> IngestedFile | None:
            async with semaphore:
                content = await self.get_file_content(repo, item["path"])
                if content is None:
                    return None
                return IngestedFile(path=item["path"], content=content, size_bytes=item.get("size", 0))

        results = await asyncio.gather(*(fetch_one(item) for item in candidates))
        return [f for f in results if f is not None]

    # ───────────────────────── Issues ─────────────────────────

    async def fetch_issues(self, repo: RepoIdentity, state: str = "all") -> list[GitHubIssueRecord]:
        issues: list[GitHubIssueRecord] = []
        page = 1
        per_page = 100
        while len(issues) < settings.MAX_ISSUES_TO_INGEST:
            try:
                resp = await self._get(
                    f"/repos/{repo.full_name}/issues",
                    params={"state": state, "per_page": per_page, "page": page},
                )
            except GitHubAPIError:
                # GitHub stops paginating list endpoints around 1000 results (422).
                # Not a hard failure — just means we've hit the API's pagination ceiling.
                logger.warning("issue_pagination_limit_reached", repo=repo.full_name, page=page)
                break
            batch = resp.json()
            if not batch:
                break
            for item in batch:
                # GitHub's /issues endpoint also returns PRs; skip those here.
                if "pull_request" in item:
                    continue
                issues.append(
                    GitHubIssueRecord(
                        number=item["number"],
                        title=item["title"],
                        body=item.get("body") or "",
                        state=item["state"],
                        url=item["html_url"],
                        labels=[lbl["name"] for lbl in item.get("labels", []) if isinstance(lbl, dict)],
                    )
                )
            page += 1
            if len(batch) < per_page:
                break
        return issues[: settings.MAX_ISSUES_TO_INGEST]

    # ───────────────────────── Pull Requests ─────────────────────────

    async def fetch_pull_requests(self, repo: RepoIdentity, state: str = "all") -> list[dict]:
        resp = await self._get(
            f"/repos/{repo.full_name}/pulls",
            params={"state": state, "per_page": 50},
        )
        prs = resp.json()
        return [
            {
                "number": pr["number"],
                "title": pr["title"],
                "body": pr.get("body") or "",
                "state": pr["state"],
                "url": pr["html_url"],
                "merged": pr.get("merged_at") is not None,
            }
            for pr in prs
        ]
