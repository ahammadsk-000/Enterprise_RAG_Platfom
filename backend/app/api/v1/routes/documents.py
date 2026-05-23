"""Document ingestion & management endpoints (tenant-scoped, RBAC-gated)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.api.deps import CurrentPrincipal, DocumentServiceDep, require_permission
from app.core.exceptions import ValidationError
from app.domains.documents.schemas.document import (
    DocumentContent,
    DocumentContentUpdate,
    DocumentList,
    DocumentRead,
    DocumentStatusResponse,
    IngestionJobRead,
    UploadResponse,
)
from app.domains.identity.permissions import Permission

router = APIRouter()

_MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_WRITE))],
)
async def upload_document(
    principal: CurrentPrincipal,
    service: DocumentServiceDep,
    file: UploadFile = File(...),
    workspace_id: uuid.UUID | None = Query(default=None),
) -> UploadResponse:
    """Upload a file; it is stored and queued for async ingestion."""
    data = await file.read()
    if not data:
        raise ValidationError("Uploaded file is empty.")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise ValidationError("File exceeds the maximum upload size (100 MB).")

    assert principal.organization_id is not None
    document, duplicate = await service.upload(
        organization_id=principal.organization_id,
        workspace_id=workspace_id,
        created_by=principal.user_id,
        filename=file.filename or "untitled",
        content_type=file.content_type,
        data=data,
    )
    return UploadResponse(document=DocumentRead.model_validate(document), duplicate=duplicate)


@router.get(
    "",
    response_model=DocumentList,
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_READ))],
)
async def list_documents(
    principal: CurrentPrincipal,
    service: DocumentServiceDep,
    workspace_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DocumentList:
    assert principal.organization_id is not None
    items, total = await service.list(
        principal.organization_id, workspace_id=workspace_id, limit=limit, offset=offset
    )
    return DocumentList(
        items=[DocumentRead.model_validate(d) for d in items], total=total, limit=limit, offset=offset
    )


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_READ))],
)
async def get_document(
    document_id: uuid.UUID, principal: CurrentPrincipal, service: DocumentServiceDep
) -> DocumentRead:
    assert principal.organization_id is not None
    document = await service.get(document_id, principal.organization_id)
    return DocumentRead.model_validate(document)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_READ))],
)
async def document_status(
    document_id: uuid.UUID, principal: CurrentPrincipal, service: DocumentServiceDep
) -> DocumentStatusResponse:
    assert principal.organization_id is not None
    document, jobs, chunk_count = await service.status(document_id, principal.organization_id)
    return DocumentStatusResponse(
        document_id=document.id,
        status=document.status,  # type: ignore[arg-type]
        chunk_count=chunk_count,
        jobs=[IngestionJobRead.model_validate(j) for j in jobs],
    )


@router.get(
    "/{document_id}/content",
    response_model=DocumentContent,
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_READ))],
)
async def get_document_content(
    document_id: uuid.UUID, principal: CurrentPrincipal, service: DocumentServiceDep
) -> DocumentContent:
    """Return the editable text of a document (None for binary/non-text files)."""
    assert principal.organization_id is not None
    document, content, editable = await service.get_content(document_id, principal.organization_id)
    return DocumentContent(
        document_id=document.id,
        title=document.title,
        mime_type=document.mime_type,
        editable=editable,
        content=content,
    )


@router.put(
    "/{document_id}/content",
    response_model=DocumentRead,
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_WRITE))],
)
async def update_document_content(
    document_id: uuid.UUID,
    body: DocumentContentUpdate,
    principal: CurrentPrincipal,
    service: DocumentServiceDep,
) -> DocumentRead:
    """Save edited text; stores the new bytes and re-runs ingestion (re-chunk/embed/index)."""
    assert principal.organization_id is not None
    document = await service.update_content(document_id, principal.organization_id, body.content)
    return DocumentRead.model_validate(document)


@router.get(
    "/{document_id}/download",
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_READ))],
)
async def download_document(
    document_id: uuid.UUID, principal: CurrentPrincipal, service: DocumentServiceDep
) -> Response:
    """Download the raw stored file."""
    assert principal.organization_id is not None
    document, data = await service.read_bytes(document_id, principal.organization_id)
    return Response(
        content=data,
        media_type=document.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{document.title}"'},
    )


@router.post(
    "/{document_id}/reindex",
    response_model=DocumentRead,
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_WRITE))],
)
async def reindex_document(
    document_id: uuid.UUID, principal: CurrentPrincipal, service: DocumentServiceDep
) -> DocumentRead:
    """Re-run chunking + embedding for a document (e.g. after changing strategy/model)."""
    assert principal.organization_id is not None
    document = await service.reindex(document_id, principal.organization_id)
    return DocumentRead.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.DOCUMENTS_DELETE))],
)
async def delete_document(
    document_id: uuid.UUID, principal: CurrentPrincipal, service: DocumentServiceDep
) -> None:
    assert principal.organization_id is not None
    await service.delete(document_id, principal.organization_id)
