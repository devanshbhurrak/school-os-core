"""Report / export routes."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.reports import repository, service
from app.modules.reports.permissions import P_EXPORT_CREATE, P_EXPORT_LIST, P_EXPORT_READ
from app.modules.reports.schemas import ExportJobListParams, ExportJobRead, ExportRequest

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/export", response_model=ExportJobRead, status_code=status.HTTP_201_CREATED)
async def create_export(
    data: ExportRequest,
    ctx: RequestContext = Depends(require(P_EXPORT_CREATE)),
    session: SessionDep = None,
):
    job, _csv_bytes = await service.request_export(session, ctx, data)
    return ExportJobRead.model_validate(job)


@router.get("/jobs", response_model=CursorPage[ExportJobRead])
async def list_export_jobs(
    params: CursorParams = Depends(),
    status_filter: str | None = None,
    ctx: RequestContext = Depends(require(P_EXPORT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    page = await repository.list_jobs(session, ctx.school_id, params, status=status_filter)
    page.items = [ExportJobRead.model_validate(j) for j in page.items]
    return page


@router.get("/jobs/{job_id}", response_model=ExportJobRead)
async def get_export_job(
    job_id: str,
    ctx: RequestContext = Depends(require(P_EXPORT_READ)),
    session: SessionDep = None,
):
    job = await service.get_job(session, ctx, job_id)
    return ExportJobRead.model_validate(job)


@router.get("/jobs/{job_id}/download")
async def download_export(
    job_id: str,
    ctx: RequestContext = Depends(require(P_EXPORT_READ)),
    session: SessionDep = None,
):
    job, csv_bytes = await service.get_download(session, ctx, job_id)
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job.report_type}_{job.id}.csv"'},
    )
