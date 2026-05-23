"""Agent run + step repository."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agents.models.agent_run import AgentRun, AgentStep


class AgentRunRepository(Protocol):
    async def add_run(self, run: AgentRun) -> AgentRun: ...
    async def add_steps(self, steps: list[AgentStep]) -> None: ...


class SqlAlchemyAgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_run(self, run: AgentRun) -> AgentRun:
        self._session.add(run)
        await self._session.flush()
        return run

    async def add_steps(self, steps: list[AgentStep]) -> None:
        self._session.add_all(steps)
        await self._session.flush()
