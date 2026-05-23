"""Conversation + Message repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chat.models.conversation import Conversation, Message


class ConversationRepository(Protocol):
    async def add(self, conversation: Conversation) -> Conversation: ...
    async def get(self, conversation_id: uuid.UUID) -> Conversation | None: ...
    async def list_for_user(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> Sequence[Conversation]: ...
    async def touch(self, conversation: Conversation) -> None: ...
    async def delete(self, conversation: Conversation) -> None: ...


class MessageRepository(Protocol):
    async def add(self, message: Message) -> Message: ...
    async def list_for_conversation(self, conversation_id: uuid.UUID, limit: int = 50) -> Sequence[Message]: ...
    async def recent(self, conversation_id: uuid.UUID, limit: int = 10) -> Sequence[Message]: ...


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversation: Conversation) -> Conversation:
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self._session.get(Conversation, conversation_id)

    async def list_for_user(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> Sequence[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.organization_id == organization_id, Conversation.user_id == user_id)
            .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc())
        )
        return result.scalars().all()

    async def touch(self, conversation: Conversation) -> None:
        conversation.last_message_at = datetime.now(UTC)
        await self._session.flush()

    async def delete(self, conversation: Conversation) -> None:
        await self._session.delete(conversation)
        await self._session.flush()


class SqlAlchemyMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: Message) -> Message:
        self._session.add(message)
        await self._session.flush()
        return message

    async def list_for_conversation(self, conversation_id: uuid.UUID, limit: int = 50) -> Sequence[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def recent(self, conversation_id: uuid.UUID, limit: int = 10) -> Sequence[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
