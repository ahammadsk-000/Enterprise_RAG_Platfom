"""Evaluation service — runs a dataset through the model and scores it.

For each sample an answer is generated from the sample's own gold contexts (offline
eval over a golden set, independent of the live index), then scored with the
heuristic metrics. Per-sample results + an aggregate mean are persisted as an EvalRun.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domains.evaluation.metrics.heuristics import evaluate_sample
from app.domains.evaluation.models.evaluation import EvalDataset, EvalResult, EvalRun, EvalSample
from app.domains.evaluation.repositories.eval_repository import EvalRepository
from app.domains.evaluation.schemas import DatasetCreate, EvalRunResult, SampleResult
from app.integrations.llm.base import ChatMessage, LLMProvider

_SYSTEM = "Answer the question using only the provided sources. Cite sources as [n]."


class EvalService:
    def __init__(self, session: AsyncSession, repo: EvalRepository, llm: LLMProvider) -> None:
        self._session = session
        self._repo = repo
        self._llm = llm

    async def create_dataset(
        self, *, organization_id: uuid.UUID, data: DatasetCreate
    ) -> EvalDataset:
        dataset = await self._repo.add_dataset(
            EvalDataset(organization_id=organization_id, name=data.name, kind=data.kind)
        )
        await self._repo.add_samples(
            [
                EvalSample(
                    dataset_id=dataset.id,
                    question=s.question,
                    ground_truth=s.ground_truth,
                    contexts=s.contexts,
                )
                for s in data.samples
            ]
        )
        await self._session.commit()
        return dataset

    async def list_datasets(self, organization_id: uuid.UUID) -> Sequence[EvalDataset]:
        return await self._repo.list_datasets(organization_id)

    async def run(self, *, dataset_id: uuid.UUID, organization_id: uuid.UUID) -> EvalRunResult:
        dataset = await self._repo.get_dataset(dataset_id)
        if dataset is None or dataset.organization_id != organization_id:
            raise NotFoundError("Dataset not found.")

        samples = await self._repo.list_samples(dataset_id)
        results: list[SampleResult] = []
        records: list[EvalResult] = []
        aggregate: dict[str, float] = {}

        run = await self._repo.add_run(EvalRun(dataset_id=dataset_id, config={"metrics": "heuristic"}))

        for sample in samples:
            answer = await self._answer(sample)
            scores = evaluate_sample(
                question=sample.question,
                answer=answer,
                contexts=list(sample.contexts),
                ground_truth=sample.ground_truth,
            )
            records.append(EvalResult(eval_run_id=run.id, sample_id=sample.id, answer=answer, scores=scores))
            results.append(SampleResult(sample_id=sample.id, question=sample.question, answer=answer, scores=scores))
            for key, value in scores.items():
                aggregate[key] = aggregate.get(key, 0.0) + value

        n = max(1, len(samples))
        metrics = {k: round(v / n, 3) for k, v in aggregate.items()}
        run.metrics = metrics
        await self._repo.add_results(records)
        await self._session.commit()

        return EvalRunResult(
            run_id=run.id, dataset_id=dataset_id, metrics=metrics, sample_count=len(samples), results=results
        )

    async def _answer(self, sample: EvalSample) -> str:
        sources = "\n\n".join(f"[{i}] {c}" for i, c in enumerate(sample.contexts, start=1)) or "(no sources)"
        messages = [
            ChatMessage(role="system", content=_SYSTEM),
            ChatMessage(role="user", content=f"Sources:\n{sources}\n\nQuestion: {sample.question}"),
        ]
        result = await self._llm.generate(messages, temperature=0.0)
        return result.text
