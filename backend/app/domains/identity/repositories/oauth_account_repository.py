"""OAuth account repository: lookup/link external SSO identities."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.models.oauth_account import OAuthAccount


class OAuthAccountRepository(Protocol):
    async def get(self, provider: str, provider_account_id: str) -> OAuthAccount | None: ...
    async def add(self, account: OAuthAccount) -> OAuthAccount: ...


class SqlAlchemyOAuthAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, provider: str, provider_account_id: str) -> OAuthAccount | None:
        result = await self._session.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_account_id == provider_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(self, account: OAuthAccount) -> OAuthAccount:
        self._session.add(account)
        await self._session.flush()
        return account
