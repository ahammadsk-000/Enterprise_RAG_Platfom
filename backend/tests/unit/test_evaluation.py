"""Unit tests for evaluation metrics + EvalService (fakes, no DB)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest

from app.domains.evaluation.metrics.heuristics import (
    answer_relevancy,
    context_recall,
    evaluate_sample,
    faithfulness,
)
from app.domains.evaluation.models.evaluation import EvalDataset, EvalResult, EvalRun, EvalSample
from app.domains.evaluation.schemas import DatasetCreate, EvalSampleIn
from app.domains.evaluation.services.eval_service import EvalService
from app.integrations.llm.fake import FakeLLMProvider


def test_faithfulness_rewards_grounded_answers() -> None:
    ctx = ["The Eiffel Tower is in Paris, France."]
    grounded = faithfulness("The Eiffel Tower is in Paris.", ctx)
    ungrounded = faithfulness("Bananas are rich in potassium.", ctx)
    assert grounded > ungrounded
    assert 0.0 <= grounded <= 1.0


def test_answer_relevancy_and_recall() -> None:
    assert answer_relevancy("capital of France", "The capital is Paris in France") > 0
    assert context_recall("Paris France", ["Paris is the capital of France"]) == 1.0


def test_evaluate_sample_returns_all_metrics() -> None:
    scores = evaluate_sample(
        question="Where is the Eiffel Tower?",
        answer="The Eiffel Tower is in Paris [1].",
        contexts=["The Eiffel Tower is located in Paris, France."],
        ground_truth="Paris",
    )
    assert {"faithfulness", "answer_relevancy", "context_precision", "hallucination", "context_recall"} <= scores.keys()
    assert scores["hallucination"] == round(1.0 - scores["faithfulness"], 3)


class _FakeEvalRepo:
    def __init__(self, dataset: EvalDataset, samples: list[EvalSample]) -> None:
        self._dataset = dataset
        self._samples = samples
        self.results: list[EvalResult] = []

    async def add_dataset(self, dataset: EvalDataset) -> EvalDataset:
        return dataset

    async def add_samples(self, samples: list[EvalSample]) -> None: ...

    async def get_dataset(self, dataset_id: uuid.UUID) -> EvalDataset | None:
        return self._dataset

    async def list_datasets(self, organization_id: uuid.UUID) -> Sequence[EvalDataset]:
        return [self._dataset]

    async def list_samples(self, dataset_id: uuid.UUID) -> Sequence[EvalSample]:
        return self._samples

    async def add_run(self, run: EvalRun) -> EvalRun:
        if run.id is None:
            run.id = uuid.uuid4()
        return run

    async def add_results(self, results: list[EvalResult]) -> None:
        self.results.extend(results)


class _FakeSession:
    async def commit(self) -> None: ...


@pytest.mark.asyncio
async def test_eval_run_aggregates_metrics() -> None:
    org = uuid.uuid4()
    dataset = EvalDataset(id=uuid.uuid4(), organization_id=org, name="golden", kind="qa")
    samples = [
        EvalSample(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            question="What is the capital of France?",
            ground_truth="Paris",
            contexts=["Paris is the capital of France."],
        )
    ]
    repo = _FakeEvalRepo(dataset, samples)
    service = EvalService(_FakeSession(), repo, FakeLLMProvider())

    result = await service.run(dataset_id=dataset.id, organization_id=org)
    assert result.sample_count == 1
    assert "faithfulness" in result.metrics
    assert len(result.results) == 1
    assert repo.results and repo.results[0].scores


@pytest.mark.asyncio
async def test_create_dataset_builds_samples() -> None:
    # exercises the DatasetCreate → samples mapping shape (no persistence assertions)
    data = DatasetCreate(name="d", samples=[EvalSampleIn(question="q", contexts=["c"])])
    assert data.samples[0].question == "q"
