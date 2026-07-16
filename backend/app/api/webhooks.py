"""
GitHub Webhook endpoint.

When a new issue is opened in a watched repository, GitHub sends a POST
to this endpoint. We verify the signature (HMAC-SHA256), then enqueue
an automatic triage task.

Decision: webhook verification is mandatory — without it, anyone on the
internet can trigger your agent by posting to this endpoint. GitHub signs
every webhook with a shared secret using HMAC-SHA256; we compare the
signature before processing anything.

Setup: in your GitHub repo → Settings → Webhooks → Add webhook:
  Payload URL: https://your-domain.com/api/v1/webhooks/github
  Content type: application/json
  Secret: value of GITHUB_WEBHOOK_SECRET in your .env
  Events: Issues
"""
from __future__ import annotations

import hashlib
import hmac
import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.crud import create_webhook_event, get_repository, update_webhook_event
from app.db.engine import get_session_factory

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter()


def _verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub's HMAC-SHA256 webhook signature."""
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
):
    payload = await request.body()

    if not x_hub_signature_256 or not _verify_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if x_github_event != "issues":
        return {"status": "ignored", "event": x_github_event}

    data = await request.json()
    action = data.get("action")
    if action not in ("opened", "reopened"):
        return {"status": "ignored", "action": action}

    issue = data.get("issue", {})
    repo = data.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    repo_id = f"{owner}__{repo_name}"
    issue_number = issue.get("number")
    issue_title = issue.get("title", "")
    issue_body = issue.get("body", "") or ""

    logger.info("webhook_received", repo_id=repo_id, issue=issue_number, action=action)

    background_tasks.add_task(
        _auto_triage_issue,
        repo_id=repo_id,
        issue_number=issue_number,
        issue_title=issue_title,
        issue_body=issue_body,
    )

    return {"status": "accepted", "issue": issue_number}


async def _auto_triage_issue(
    repo_id: str,
    issue_number: int,
    issue_title: str,
    issue_body: str,
):
    """Background: run triage on webhook-triggered issue and post reply to GitHub."""
    from app.agents.graph import run_triage
    from app.models.schemas import RepositoryStatus
    from app.rag.registry import get_repo_registry

    async with get_session_factory()() as db:
        event = await create_webhook_event(
            db,
            repo_id=repo_id,
            github_issue_number=issue_number,
            github_issue_title=issue_title,
            event_type="issues.opened",
            status="processing",
        )
        await db.commit()

        try:
            registry = get_repo_registry()
            record = registry.get(repo_id)
            if not record or record.status != RepositoryStatus.READY:
                raise ValueError(f"Repository {repo_id} not indexed — index it first via /analyze-repository")

            analysis_id = str(uuid.uuid4())
            final_state = await run_triage(
                repo_id=repo_id,
                issue_title=issue_title,
                issue_description=issue_body,
                thread_id=analysis_id,
                analysis_id=analysis_id,
            )

            # Post the generated reply back to GitHub
            if settings.GITHUB_TOKEN:
                await _post_github_comment(
                    repo_id=repo_id,
                    issue_number=issue_number,
                    comment=final_state.get("generated_response", ""),
                )

            await update_webhook_event(db, event.id, status="completed", analysis_id=analysis_id)
            await db.commit()
            logger.info("webhook_triage_complete", repo_id=repo_id, issue=issue_number)

        except Exception as exc:
            logger.error("webhook_triage_failed", repo_id=repo_id, issue=issue_number, error=str(exc))
            await update_webhook_event(db, event.id, status="failed", error=str(exc))
            await db.commit()


async def _post_github_comment(repo_id: str, issue_number: int, comment: str):
    """Post the generated triage reply directly to the GitHub issue."""
    import httpx
    owner, name = repo_id.split("__", 1)
    url = f"https://api.github.com/repos/{owner}/{name}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"body": comment}, headers=headers)
        resp.raise_for_status()
    logger.info("github_comment_posted", repo_id=repo_id, issue=issue_number)
