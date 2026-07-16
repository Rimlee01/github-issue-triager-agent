"""
Database engine and session management — lazy initialization.

Decision: we defer engine creation until first use rather than at module
import time. This means tests and scripts that don't need a real database
can import the app without asyncpg installed, and the healthcheck can
succeed even if DB is temporarily unavailable during startup.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import Base

settings = get_settings()

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


# Convenience alias used by Celery tasks
class AsyncSessionLocal:
    def __new__(cls):
        return get_session_factory()()

    def __class_getitem__(cls, item):
        return get_session_factory()


async def init_db() -> None:
    """Create all tables on startup if they don't exist."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency that provides a database session per request."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
