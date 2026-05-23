"""Agent service — runs the research graph and persists the run + steps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agents.graph.orchestrator import ResearchAgentGraph
from app.domains.agents.models.agent_run import AgentRun, AgentStep
from app.domains.agents.repositories.agent_repository import AgentRunRepository
from app.domains.agents.schemas import AgentResearchRequest, AgentResearchResponse, AgentStepOut


class AgentService:
    def __init__(self, session: AsyncSession, graph: ResearchAgentGraph, runs: AgentRunRepository) -> None:
        self._session = session
        self._graph = graph
        self._runs = runs

    async def research(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID | None, req: AgentResearchRequest
    ) -> AgentResearchResponse:
        started = datetime.now(UTC)
        result = await self._graph.run(
            organization_id=organization_id,
            workspace_id=req.workspace_id,
            user_id=user_id,
            query=req.query,
            top_k=req.top_k,
        )

        run = await self._runs.add_run(
            AgentRun(
                organization_id=organization_id,
                workspace_id=req.workspace_id,
                user_id=user_id,
                graph_name="research",
                status="succeeded" if result.verified else "unverified",
                query=req.query,
                answer=result.answer,
                confidence=result.confidence,
                total_tokens=result.total_tokens,
                started_at=started,
                finished_at=datetime.now(UTC),
                output={"sub_questions": result.sub_questions, "citations": len(result.citations)},
            )
        )
        await self._runs.add_steps(
            [
                AgentStep(
                    agent_run_id=run.id,
                    ordinal=i,
                    node_name=step.node,
                    role=step.role,
                    output=step.output,
                    latency_ms=step.latency_ms,
                )
                for i, step in enumerate(result.steps)
            ]
        )
        await self._session.commit()

        return AgentResearchResponse(
            run_id=run.id,
            answer=result.answer,
            citations=result.citations,
            confidence=result.confidence,
            verified=result.verified,
            sub_questions=result.sub_questions,
            steps=[AgentStepOut(node=s.node, role=s.role, output=s.output, latency_ms=s.latency_ms) for s in result.steps],
            total_tokens=result.total_tokens,
        )
