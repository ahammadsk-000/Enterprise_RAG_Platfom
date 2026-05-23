"""Retrieval log repository (append-only)."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.retrieval.models.retrieval_log import RetrievalLog


class RetrievalLogRepository(Protocol):
    async def add(self, log: RetrievalLog) -> RetrievalLog: ...


class SqlAlchemyRetrievalLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: RetrievalLog) -> RetrievalLog:
        self._session.add(log)
        await self._session.flush()
        return log
