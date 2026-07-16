"""FastAPI application — v2 with SSE progress streaming."""
from __future__ import annotations

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.routes import router as api_router
from app.api.webhooks import router as webhook_router
from app.api.sse import router as sse_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.engine import init_db

settings = get_settings()
configure_logging(debug=settings.DEBUG)
logger = get_logger(__name__)

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.2)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


def _preload_embeddings():
    """Pre-load embedding model at startup so first triage is fast."""
    try:
        from app.rag.embeddings import get_embedding_model
        get_embedding_model()
        logger.info("embedding_model_preloaded")
    except Exception as exc:
        logger.warning("embedding_preload_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", version=settings.APP_VERSION)

    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as exc:
        logger.warning("database_init_failed", error=str(exc))

    # Pre-load embedding model in a thread so it doesn't block the event loop
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _preload_embeddings)

    if not settings.GROQ_API_KEY:
        logger.warning("missing_groq_api_key")

    yield
    logger.info("app_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade AI agent for GitHub issue triage",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=str(request.url), error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


app.include_router(api_router, prefix="/api/v1", tags=["triage"])
app.include_router(webhook_router, prefix="/api/v1", tags=["webhooks"])
app.include_router(sse_router, prefix="/api/v1", tags=["progress"])
