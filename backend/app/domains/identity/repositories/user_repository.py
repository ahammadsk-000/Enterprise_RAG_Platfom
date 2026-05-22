"""User repository: interface + SQLAlchemy implementation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.models.user import User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def add(self, user: User) -> User: ...
    async def touch_last_login(self, user: User) -> None: ...


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def touch_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()
