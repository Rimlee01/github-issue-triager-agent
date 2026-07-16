"""
Celery application configuration.

Decision: Celery + Redis for background task queue rather than FastAPI's
built-in BackgroundTasks. BackgroundTasks share the web process and block
under heavy load; Celery workers run in separate processes, can be scaled
independently, have proper retry logic, and are visible in Flower dashboard.

This is the production pattern — interview interviewers specifically ask
"how would you handle long-running tasks?" and this is the correct answer.
"""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "triager",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.ingestion_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # only ack after task completes — prevents lost tasks on worker crash
    worker_prefetch_multiplier=1,  # fair dispatch — don't prefetch more than one task per worker
    task_routes={
        "app.tasks.ingestion_task.ingest_repository_task": {"queue": "ingestion"},
    },
)
