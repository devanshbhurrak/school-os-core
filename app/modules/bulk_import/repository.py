"""ImportJob repository — thin DB access layer."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bulk_import.enums import ImportJobStatus, ImportResourceType
from app.modules.bulk_import.models import ImportJob


async def create_job(session: AsyncSession, job_data: dict) -> ImportJob:
    job = ImportJob(**job_data)
    session.add(job)
    await session.flush()
    return job


async def get_by_id(session: AsyncSession, id: str, school_id: str) -> ImportJob | None:
    stmt = select(ImportJob).where(
        ImportJob.id == id,
        ImportJob.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()


async def list_jobs(
    session: AsyncSession,
    school_id: str,
    *,
    resource_type: ImportResourceType | None = None,
    status: ImportJobStatus | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> list[ImportJob]:
    stmt = (
        select(ImportJob)
        .where(ImportJob.school_id == school_id)
        .order_by(ImportJob.created_at.desc())
        .limit(limit)
    )
    if resource_type is not None:
        stmt = stmt.where(ImportJob.resource_type == resource_type.value)
    if status is not None:
        stmt = stmt.where(ImportJob.status == status.value)
    if cursor is not None:
        stmt = stmt.where(ImportJob.id < cursor)
    return list((await session.scalars(stmt)).all())


async def update_job(session: AsyncSession, job: ImportJob, updates: dict) -> ImportJob:
    for field, value in updates.items():
        setattr(job, field, value)
    await session.flush()
    return job
