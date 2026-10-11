"""Document business logic (Phase 3: size + MIME hardened)."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.errors import FileTooLargeError, InvalidRequestError, NotFoundError, RequestTimeoutError
from app.core.pagination import CursorPage
from app.modules.documents import repository
from app.modules.documents.enums import DocumentStatus
from app.modules.documents.models import Document
from app.modules.documents.schemas import DocumentListParams, DocumentUploadRequest, DocumentUploadResponse, DocumentDownloadResponse
from app.modules.documents.storage import (
    detect_mime,
    generate_download_url,
    generate_upload_url,
    get_object_bytes,
    head_object_info,
)
from app.modules.platform_.audit.service import audit

_SNAPSHOT_FIELDS = ["original_filename", "document_type", "entity_type", "entity_id", "status"]


def _document_snapshot(doc: Document) -> dict:
    return {field: getattr(doc, field) for field in _SNAPSHOT_FIELDS}


async def request_upload(
    session: AsyncSession, ctx: RequestContext, payload: DocumentUploadRequest
) -> DocumentUploadResponse:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # A2: enforce max file size at pre-signed URL generation time.
    settings = get_settings()
    declared_size = payload.file_size
    if declared_size > settings.max_upload_size_bytes:
        raise FileTooLargeError(
            f"File is too large ({declared_size} bytes). "
            f"Maximum allowed is {settings.max_upload_size_bytes} bytes.",
            details={"max_bytes": settings.max_upload_size_bytes, "actual_bytes": declared_size},
        )
    if payload.mime_type not in settings.allowed_mime_types:
        raise InvalidRequestError(
            f"MIME type {payload.mime_type!r} is not allowed."
        )

    doc = Document(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        document_type=payload.document_type,
        original_filename=payload.original_filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        status=DocumentStatus.PENDING_UPLOAD.value,
        created_by_id=ctx.user_id,
    )
    await repository.create(session, doc)

    storage_key = (
        f"{ctx.organization_id}/{ctx.school_id}/{payload.entity_type}"
        f"/{payload.entity_id}/{doc.id}/{payload.original_filename}"
    )
    doc.storage_key = storage_key
    await session.flush()

    upload_url = generate_upload_url(storage_key, payload.mime_type)

    await audit(
        session, ctx,
        action="DOCUMENT_UPLOAD_REQUESTED",
        entity_type="document",
        entity_id=doc.id,
        summary=f"Upload requested for {payload.original_filename!r}",
        after=_document_snapshot(doc),
    )

    return DocumentUploadResponse(id=doc.id, upload_url=upload_url, storage_key=storage_key)


async def confirm_upload(session: AsyncSession, ctx: RequestContext, document_id: str) -> Document:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    doc = await repository.get_by_id(session, ctx.school_id, document_id, organization_id=ctx.organization_id)
    if doc is None:
        raise NotFoundError("The document was not found.", code="DOCUMENT_NOT_FOUND")

    if doc.status != DocumentStatus.PENDING_UPLOAD.value:
        raise InvalidRequestError("Document is not pending upload.")

    # A2 + A4: HEAD the object with a bounded timeout; reject oversize.
    settings = get_settings()
    try:
        info = await asyncio.to_thread(
            head_object_info, doc.storage_key,
            settings.document_confirm_timeout_seconds,
        )
    except TimeoutError as exc:
        raise RequestTimeoutError(
            "Storage verification timed out. Please retry."
        ) from exc
    if info is None:
        raise InvalidRequestError("The file has not been uploaded to storage yet.")
    if info.size_bytes > settings.max_upload_size_bytes:
        raise FileTooLargeError(
            f"Uploaded file is too large ({info.size_bytes} bytes). "
            f"Maximum allowed is {settings.max_upload_size_bytes} bytes.",
            details={"max_bytes": settings.max_upload_size_bytes, "actual_bytes": info.size_bytes},
        )

    # A2: validate magic bytes — reject spoofed extensions (.exe renamed .pdf).
    try:
        sample = await asyncio.to_thread(get_object_bytes, doc.storage_key)
    except TimeoutError as exc:
        raise RequestTimeoutError(
            "Storage verification timed out. Please retry."
        ) from exc
    except Exception:
        sample = b""
    if sample:
        sniffed = detect_mime(sample, doc.original_filename)
        if sniffed and sniffed not in settings.allowed_mime_types:
            raise InvalidRequestError(
                f"File content type {sniffed!r} does not match an allowed type. "
                "The file may be misnamed or disallowed."
            )
        # Cross-check: sniffed type must be compatible with declared type.
        if sniffed and doc.mime_type and sniffed != doc.mime_type:
            # Allow common aliases (jpeg/jpg, CSV text variants) to avoid
            # false rejections on benign files.
            _aliases = {
                "image/jpeg": {"image/jpeg", "image/jpg"},
                "text/csv": {"text/csv", "text/plain", "application/csv"},
                "text/plain": {"text/plain", "text/csv"},
            }
            permitted = _aliases.get(doc.mime_type, {doc.mime_type})
            if sniffed not in permitted:
                raise InvalidRequestError(
                    f"File content ({sniffed!r}) does not match declared type "
                    f"{doc.mime_type!r}."
                )

    before = _document_snapshot(doc)
    doc.status = DocumentStatus.CONFIRMED.value
    # Persist the verified size so listings never trust the client claim.
    doc.file_size = info.size_bytes
    doc.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="DOCUMENT_CONFIRMED",
        entity_type="document",
        entity_id=doc.id,
        summary=f"Document {doc.original_filename!r} confirmed",
        before=before,
        after=_document_snapshot(doc),
    )
    return doc


async def get_download_url(
    session: AsyncSession, ctx: RequestContext, document_id: str
) -> DocumentDownloadResponse:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    doc = await repository.get_by_id(session, ctx.school_id, document_id, organization_id=ctx.organization_id)
    if doc is None:
        raise NotFoundError("The document was not found.", code="DOCUMENT_NOT_FOUND")

    url = generate_download_url(doc.storage_key, doc.original_filename)

    await audit(
        session, ctx,
        action="DOCUMENT_DOWNLOADED",
        entity_type="document",
        entity_id=doc.id,
        summary=f"Download URL generated for {doc.original_filename!r}",
    )

    return DocumentDownloadResponse(download_url=url, filename=doc.original_filename)


async def list_documents(
    session: AsyncSession, ctx: RequestContext, params: DocumentListParams
) -> CursorPage[Document]:
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_documents(session, ctx.school_id, params, organization_id=ctx.organization_id)


async def delete_document(
    session: AsyncSession, ctx: RequestContext, document_id: str
) -> None:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    doc = await repository.get_by_id(session, ctx.school_id, document_id, organization_id=ctx.organization_id)
    if doc is None:
        raise NotFoundError("The document was not found.", code="DOCUMENT_NOT_FOUND")

    before = _document_snapshot(doc)
    doc.status = DocumentStatus.DELETED.value
    doc.deleted_at = datetime.now(UTC)
    doc.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="DOCUMENT_DELETED",
        entity_type="document",
        entity_id=doc.id,
        summary=f"Document {doc.original_filename!r} deleted",
        before=before,
    )
