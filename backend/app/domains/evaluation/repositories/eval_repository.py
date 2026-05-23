"""Evaluation repository (datasets, samples, runs, results)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.evaluation.models.evaluation import EvalDataset, EvalResult, EvalRun, EvalSample


class EvalRepository(Protocol):
    async def add_dataset(self, dataset: EvalDataset) -> EvalDataset: ...
    async def add_samples(self, samples: list[EvalSample]) -> None: ...
    async def get_dataset(self, dataset_id: uuid.UUID) -> EvalDataset | None: ...
    async def list_datasets(self, organization_id: uuid.UUID) -> Sequence[EvalDataset]: ...
    async def list_samples(self, dataset_id: uuid.UUID) -> Sequence[EvalSample]: ...
    async def add_run(self, run: EvalRun) -> EvalRun: ...
    async def add_results(self, results: list[EvalResult]) -> None: ...


class SqlAlchemyEvalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_dataset(self, dataset: EvalDataset) -> EvalDataset:
        self._session.add(dataset)
        await self._session.flush()
        return dataset

    async def add_samples(self, samples: list[EvalSample]) -> None:
        self._session.add_all(samples)
        await self._session.flush()

    async def get_dataset(self, dataset_id: uuid.UUID) -> EvalDataset | None:
        return await self._session.get(EvalDataset, dataset_id)

    async def list_datasets(self, organization_id: uuid.UUID) -> Sequence[EvalDataset]:
        result = await self._session.execute(
            select(EvalDataset).where(EvalDataset.organization_id == organization_id).order_by(EvalDataset.created_at.desc())
        )
        return result.scalars().all()

    async def list_samples(self, dataset_id: uuid.UUID) -> Sequence[EvalSample]:
        result = await self._session.execute(select(EvalSample).where(EvalSample.dataset_id == dataset_id))
        return result.scalars().all()

    async def add_run(self, run: EvalRun) -> EvalRun:
        self._session.add(run)
        await self._session.flush()
        return run

    async def add_results(self, results: list[EvalResult]) -> None:
        self._session.add_all(results)
        await self._session.flush()
