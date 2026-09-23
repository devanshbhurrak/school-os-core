"""Attendance data access — school-scoped."""
from __future__ import annotations

from datetime import date

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.attendance.enums import AttendanceSessionStatus
from app.modules.attendance.models import AttendanceRecord, AttendanceSession


async def get_session_by_id(
    session: AsyncSession, session_id: str, school_id: str
) -> AttendanceSession | None:
    stmt = (
        select(AttendanceSession)
        .options(selectinload(AttendanceSession.records))
        .where(
            AttendanceSession.id == session_id,
            AttendanceSession.school_id == school_id,
        )
    )
    return (await session.scalars(stmt)).first()


async def get_session_for_cohort_date(
    session: AsyncSession, cohort_id: str, session_date: date, school_id: str
) -> AttendanceSession | None:
    stmt = select(AttendanceSession).where(
        AttendanceSession.cohort_id == cohort_id,
        AttendanceSession.session_date == session_date,
        AttendanceSession.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()


async def list_sessions(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    cohort_id: str | None = None,
    academic_year_id: str | None = None,
    status: AttendanceSessionStatus | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> CursorPage[AttendanceSession]:
    stmt = select(AttendanceSession).where(AttendanceSession.school_id == school_id)
    if cohort_id is not None:
        stmt = stmt.where(AttendanceSession.cohort_id == cohort_id)
    if academic_year_id is not None:
        stmt = stmt.where(AttendanceSession.academic_year_id == academic_year_id)
    if status is not None:
        stmt = stmt.where(AttendanceSession.status == status.value)
    if from_date is not None:
        stmt = stmt.where(AttendanceSession.session_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(AttendanceSession.session_date <= to_date)
    return await paginate_cursor(session, stmt, params, model=AttendanceSession)


async def get_record(
    session: AsyncSession, record_id: str, school_id: str
) -> AttendanceRecord | None:
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.id == record_id,
        AttendanceRecord.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()


async def list_records_for_session(
    session: AsyncSession, session_id: str, school_id: str
) -> list[AttendanceRecord]:
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.session_id == session_id,
        AttendanceRecord.school_id == school_id,
    )
    return list((await session.scalars(stmt)).all())


async def bulk_upsert_records(
    session: AsyncSession,
    session_id: str,
    records: list[dict],
    school_id: str,
) -> None:
    """INSERT ... ON CONFLICT (session_id, enrollment_id) DO UPDATE SET ..."""
    if not records:
        return
    for rec in records:
        stmt = (
            pg_insert(AttendanceRecord)
            .values(
                session_id=session_id,
                enrollment_id=rec["enrollment_id"],
                school_id=school_id,
                organization_id=rec.get("organization_id", ""),
                student_id=rec.get("student_id", ""),
                status=rec.get("status", "PRESENT"),
                arrived_at=rec.get("arrived_at"),
                notes=rec.get("notes"),
                created_by_id=rec.get("created_by_id"),
                updated_by_id=rec.get("updated_by_id"),
            )
            .on_conflict_do_update(
                constraint="uq_record_session_enrollment",
                set_={
                    "status": rec.get("status", "PRESENT"),
                    "arrived_at": rec.get("arrived_at"),
                    "notes": rec.get("notes"),
                    "updated_by_id": rec.get("updated_by_id"),
                },
            )
        )
        await session.execute(stmt)
