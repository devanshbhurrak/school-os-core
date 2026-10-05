"""Export job data access — school-scoped."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.reports.models import ExportJob


async def create_job(session: AsyncSession, job: ExportJob) -> ExportJob:
    session.add(job)
    await session.flush()
    return job


async def get_by_id(session: AsyncSession, job_id: str, school_id: str) -> ExportJob | None:
    stmt = select(ExportJob).where(
        ExportJob.id == job_id,
        ExportJob.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()


async def list_jobs(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    status: str | None = None,
) -> CursorPage[ExportJob]:
    stmt = select(ExportJob).where(ExportJob.school_id == school_id)
    if status is not None:
        stmt = stmt.where(ExportJob.status == status)
    return await paginate_cursor(session, stmt, params, model=ExportJob)


async def update_status(
    session: AsyncSession,
    job_id: str,
    status: str,
    **kwargs: Any,
) -> None:
    stmt = (
        update(ExportJob)
        .where(ExportJob.id == job_id)
        .values(status=status, **kwargs)
    )
    await session.execute(stmt)
    await session.flush()
