"""Embedding version repository (get-or-create the active version)."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.embeddings.models.embedding_version import EmbeddingVersion


class EmbeddingVersionRepository(Protocol):
    async def get_or_create(
        self, *, provider: str, model_name: str, dim: int, normalize: bool
    ) -> EmbeddingVersion: ...


class SqlAlchemyEmbeddingVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self, *, provider: str, model_name: str, dim: int, normalize: bool
    ) -> EmbeddingVersion:
        result = await self._session.execute(
            select(EmbeddingVersion).where(
                EmbeddingVersion.provider == provider,
                EmbeddingVersion.model_name == model_name,
                EmbeddingVersion.dim == dim,
            )
        )
        version = result.scalar_one_or_none()
        if version is None:
            version = EmbeddingVersion(
                provider=provider, model_name=model_name, dim=dim, normalize=normalize
            )
            self._session.add(version)
            await self._session.flush()
        return version
