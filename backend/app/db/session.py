"""Async database engine and session management.

Exposes:
- `engine` / `AsyncSessionLocal` — the global async engine + session factory.
- `get_db` — FastAPI dependency yielding a request-scoped session (unit of work).
- `dispose_engine` — graceful shutdown hook.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.db.dsn,
    echo=_settings.db.echo,
    pool_size=_settings.db.pool_size,
    max_overflow=_settings.db.max_overflow,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async session.

    The caller's use case is the unit of work: commit on success, rollback on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the engine's connection pool (call on shutdown)."""
    await engine.dispose()
