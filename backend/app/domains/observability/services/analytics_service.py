"""Admin analytics — tenant-scoped usage aggregates for the dashboard.

Read-model queries over the operational tables (documents, conversations/messages,
retrieval_logs, agent_runs). High-volume tables would be projected into summary
tables in production; here we aggregate on read.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agents.models.agent_run import AgentRun
from app.domains.chat.models.conversation import Conversation, Message
from app.domains.documents.enums import DocumentStatus
from app.domains.documents.models.document import Document
from app.domains.retrieval.models.retrieval_log import RetrievalLog


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def overview(self, organization_id: uuid.UUID) -> dict:
        documents_total = await self._count(Document, Document.organization_id == organization_id)
        documents_indexed = await self._count(
            Document,
            Document.organization_id == organization_id,
            Document.status == DocumentStatus.INDEXED.value,
        )
        conversations = await self._count(Conversation, Conversation.organization_id == organization_id)

        msg_row = (
            await self._session.execute(
                select(
                    func.count(Message.id),
                    func.coalesce(func.sum(Message.prompt_tokens + Message.completion_tokens), 0),
                    func.avg(Message.confidence),
                )
                .select_from(Message)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(Conversation.organization_id == organization_id)
            )
        ).one()

        retr_row = (
            await self._session.execute(
                select(func.count(RetrievalLog.id), func.avg(RetrievalLog.latency_ms)).where(
                    RetrievalLog.organization_id == organization_id
                )
            )
        ).one()

        agent_runs = await self._count(AgentRun, AgentRun.organization_id == organization_id)

        return {
            "documents_total": documents_total,
            "documents_indexed": documents_indexed,
            "conversations": conversations,
            "messages": int(msg_row[0] or 0),
            "total_tokens": int(msg_row[1] or 0),
            "avg_confidence": round(float(msg_row[2]), 3) if msg_row[2] is not None else None,
            "retrieval_queries": int(retr_row[0] or 0),
            "avg_retrieval_latency_ms": round(float(retr_row[1]), 2) if retr_row[1] is not None else None,
            "agent_runs": agent_runs,
        }

    async def _count(self, model: type, *conditions) -> int:  # type: ignore[no-untyped-def]
        total = await self._session.scalar(select(func.count()).select_from(model).where(*conditions))
        return int(total or 0)
