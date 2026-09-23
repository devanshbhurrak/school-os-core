"""Bulk import/export routes."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage
from app.db.session import SessionDep
from app.modules.bulk_import import repository, service
from app.modules.bulk_import.csv_helpers import STUDENT_COLUMNS, TEACHER_COLUMNS
from app.modules.bulk_import.enums import ImportJobStatus, ImportResourceType
from app.modules.bulk_import.permissions import (
    EXPORT_CREATE,
    IMPORT_CREATE,
    IMPORT_LIST,
    IMPORT_READ,
)
from app.modules.bulk_import.schemas import ImportJobRead

router = APIRouter(tags=["bulk-import"])


@router.get("/import-jobs", response_model=list[ImportJobRead])
async def list_import_jobs(
    resource_type: ImportResourceType | None = None,
    status: ImportJobStatus | None = None,
    cursor: str | None = None,
    limit: int = 20,
    ctx: RequestContext = Depends(require(IMPORT_LIST)),
    session: SessionDep = None,
) -> list[ImportJobRead]:
    if ctx.school_id is None:
        return []
    jobs = await repository.list_jobs(
        session,
        ctx.school_id,
        resource_type=resource_type,
        status=status,
        cursor=cursor,
        limit=limit,
    )
    return [ImportJobRead.model_validate(j) for j in jobs]


@router.get("/import-jobs/{job_id}", response_model=ImportJobRead)
async def get_import_job(
    job_id: str,
    ctx: RequestContext = Depends(require(IMPORT_READ)),
    session: SessionDep = None,
) -> ImportJobRead:
    from app.core.errors import NotFoundError

    if ctx.school_id is None:
        raise NotFoundError("The import job was not found.", code="IMPORT_JOB_NOT_FOUND")
    job = await repository.get_by_id(session, job_id, ctx.school_id)
    if job is None:
        raise NotFoundError("The import job was not found.", code="IMPORT_JOB_NOT_FOUND")
    return ImportJobRead.model_validate(job)


@router.post("/import-jobs/upload", response_model=ImportJobRead)
async def upload_import(
    resource_type: ImportResourceType = Form(...),
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(require(IMPORT_CREATE)),
    session: SessionDep = None,
) -> ImportJobRead:
    content = await file.read()
    filename = file.filename or "upload.csv"
    job = await service.start_import(session, ctx, resource_type, content, filename)
    return ImportJobRead.model_validate(job)


@router.get("/imports/template/{resource_type}")
async def download_template(
    resource_type: ImportResourceType,
    ctx: RequestContext = Depends(require(IMPORT_READ)),
) -> StreamingResponse:
    if resource_type == ImportResourceType.STUDENTS:
        headers_row = ",".join(STUDENT_COLUMNS) + "\n"
    else:
        headers_row = ",".join(TEACHER_COLUMNS) + "\n"

    return StreamingResponse(
        io.BytesIO(headers_row.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{resource_type}-template.csv"'},
    )


@router.get("/exports/{resource_type}")
async def export_records(
    resource_type: ImportResourceType,
    ctx: RequestContext = Depends(require(EXPORT_CREATE)),
    session: SessionDep = None,
) -> StreamingResponse:
    csv_bytes = await service.get_export(session, ctx, resource_type)
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{resource_type}-export.csv"'},
    )
