"""Document routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage
from app.db.session import SessionDep
from app.modules.documents import service
from app.modules.documents.permissions import (
    P_DOCUMENT_CREATE,
    P_DOCUMENT_DELETE,
    P_DOCUMENT_LIST,
    P_DOCUMENT_READ,
)
from app.modules.documents.schemas import (
    DocumentDownloadResponse,
    DocumentListParams,
    DocumentRead,
    DocumentUploadRequest,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload-url", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def request_upload_url(
    data: DocumentUploadRequest,
    ctx: RequestContext = Depends(require(P_DOCUMENT_CREATE)),
    session: SessionDep = None,
):
    return await service.request_upload(session, ctx, data)


@router.post("/{document_id}/confirm", response_model=DocumentRead)
async def confirm_upload(
    document_id: str,
    ctx: RequestContext = Depends(require(P_DOCUMENT_CREATE)),
    session: SessionDep = None,
):
    doc = await service.confirm_upload(session, ctx, document_id)
    return DocumentRead.model_validate(doc)


@router.get("/{document_id}/download-url", response_model=DocumentDownloadResponse)
async def get_download_url(
    document_id: str,
    ctx: RequestContext = Depends(require(P_DOCUMENT_READ)),
    session: SessionDep = None,
):
    return await service.get_download_url(session, ctx, document_id)


@router.get("", response_model=CursorPage[DocumentRead])
async def list_documents(
    entity_type: str | None = None,
    entity_id: str | None = None,
    document_type: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    ctx: RequestContext = Depends(require(P_DOCUMENT_LIST)),
    session: SessionDep = None,
):
    params = DocumentListParams(
        entity_type=entity_type,
        entity_id=entity_id,
        document_type=document_type,
        cursor=cursor,
        limit=limit,
    )
    page = await service.list_documents(session, ctx, params)
    page.items = [DocumentRead.model_validate(d) for d in page.items]
    return page


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    ctx: RequestContext = Depends(require(P_DOCUMENT_DELETE)),
    session: SessionDep = None,
):
    await service.delete_document(session, ctx, document_id)
