"""RAG evaluation endpoints (datasets + scored runs)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentPrincipal, EvalServiceDep, require_permission
from app.domains.evaluation.schemas import DatasetCreate, DatasetRead, EvalRunResult
from app.domains.identity.permissions import Permission

router = APIRouter()


@router.post(
    "/datasets",
    response_model=DatasetRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
async def create_dataset(
    data: DatasetCreate, principal: CurrentPrincipal, service: EvalServiceDep
) -> DatasetRead:
    assert principal.organization_id is not None
    ds = await service.create_dataset(organization_id=principal.organization_id, data=data)
    return DatasetRead.model_validate(ds)


@router.get(
    "/datasets",
    response_model=list[DatasetRead],
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
async def list_datasets(principal: CurrentPrincipal, service: EvalServiceDep) -> list[DatasetRead]:
    assert principal.organization_id is not None
    return [DatasetRead.model_validate(d) for d in await service.list_datasets(principal.organization_id)]


@router.post(
    "/datasets/{dataset_id}/run",
    response_model=EvalRunResult,
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
async def run_evaluation(
    dataset_id: uuid.UUID, principal: CurrentPrincipal, service: EvalServiceDep
) -> EvalRunResult:
    """Generate answers for every sample and score faithfulness/relevancy/precision/recall."""
    assert principal.organization_id is not None
    return await service.run(dataset_id=dataset_id, organization_id=principal.organization_id)
