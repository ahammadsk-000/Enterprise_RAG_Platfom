"""Evaluation DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvalSampleIn(BaseModel):
    question: str = Field(min_length=1)
    ground_truth: str | None = None
    contexts: list[str] = Field(default_factory=list)


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    kind: str = "qa"
    samples: list[EvalSampleIn] = Field(default_factory=list)


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    kind: str
    created_at: datetime


class SampleResult(BaseModel):
    sample_id: uuid.UUID
    question: str
    answer: str
    scores: dict[str, float]


class EvalRunResult(BaseModel):
    run_id: uuid.UUID | None
    dataset_id: uuid.UUID
    metrics: dict[str, float]
    sample_count: int
    results: list[SampleResult]
