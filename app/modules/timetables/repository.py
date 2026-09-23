"""Timetable data access — school-scoped."""
from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.teachers.models import Teacher
from app.modules.timetables.enums import TimetableSlotStatus
from app.modules.timetables.models import PeriodDefinition, TimetableSlot


# ---------------------------------------------------------------------------
# Period Definitions
# ---------------------------------------------------------------------------


async def get_period_by_id(
    session: AsyncSession, school_id: str, period_id: str
) -> PeriodDefinition | None:
    stmt = select(PeriodDefinition).where(
        PeriodDefinition.id == period_id,
        PeriodDefinition.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()


async def get_period_by_name(
    session: AsyncSession, school_id: str, academic_year_id: str, name: str
) -> PeriodDefinition | None:
    stmt = select(PeriodDefinition).where(
        PeriodDefinition.school_id == school_id,
        PeriodDefinition.academic_year_id == academic_year_id,
        PeriodDefinition.name == name,
    )
    return (await session.scalars(stmt)).first()


async def list_for_year(
    session: AsyncSession,
    school_id: str,
    academic_year_id: str,
    *,
    cursor: str | None = None,
    limit: int = 50,
) -> CursorPage[PeriodDefinition]:
    params = CursorParams(cursor=cursor, limit=limit)
    stmt = select(PeriodDefinition).where(
        PeriodDefinition.school_id == school_id,
        PeriodDefinition.academic_year_id == academic_year_id,
    ).order_by(PeriodDefinition.sort_order, PeriodDefinition.id)
    return await paginate_cursor(session, stmt, params, model=PeriodDefinition)


# ---------------------------------------------------------------------------
# Timetable Slots
# ---------------------------------------------------------------------------


async def get_slot_by_id(
    session: AsyncSession, school_id: str, slot_id: str
) -> TimetableSlot | None:
    stmt = (
        select(TimetableSlot)
        .options(
            selectinload(TimetableSlot.teacher).selectinload(Teacher.person),
            selectinload(TimetableSlot.subject),
            selectinload(TimetableSlot.cohort),
            selectinload(TimetableSlot.period_definition),
        )
        .where(
            TimetableSlot.id == slot_id,
            TimetableSlot.school_id == school_id,
        )
    )
    return (await session.scalars(stmt)).first()


async def list_for_cohort(
    session: AsyncSession,
    cohort_id: str,
    school_id: str,
    *,
    academic_year_id: str | None = None,
    day_of_week: str | None = None,
    cursor: str | None = None,
    limit: int = 200,
) -> CursorPage[TimetableSlot]:
    params = CursorParams(cursor=cursor, limit=limit)
    stmt = select(TimetableSlot).where(
        TimetableSlot.cohort_id == cohort_id,
        TimetableSlot.school_id == school_id,
    )
    if academic_year_id:
        stmt = stmt.where(TimetableSlot.academic_year_id == academic_year_id)
    if day_of_week:
        stmt = stmt.where(TimetableSlot.day_of_week == day_of_week)
    return await paginate_cursor(session, stmt, params, model=TimetableSlot)


async def list_for_teacher(
    session: AsyncSession,
    teacher_id: str,
    school_id: str,
    *,
    academic_year_id: str | None = None,
    day_of_week: str | None = None,
    cursor: str | None = None,
    limit: int = 200,
) -> CursorPage[TimetableSlot]:
    params = CursorParams(cursor=cursor, limit=limit)
    stmt = select(TimetableSlot).where(
        TimetableSlot.teacher_id == teacher_id,
        TimetableSlot.school_id == school_id,
    )
    if academic_year_id:
        stmt = stmt.where(TimetableSlot.academic_year_id == academic_year_id)
    if day_of_week:
        stmt = stmt.where(TimetableSlot.day_of_week == day_of_week)
    return await paginate_cursor(session, stmt, params, model=TimetableSlot)


async def check_teacher_conflict(
    session: AsyncSession,
    teacher_id: str,
    period_definition_id: str,
    day_of_week: str,
    effective_from: date,
    effective_to: date | None,
    *,
    exclude_id: str | None = None,
) -> bool:
    """Return True if teacher already has an ACTIVE slot at that period+day with overlapping dates."""
    stmt = select(TimetableSlot.id).where(
        TimetableSlot.teacher_id == teacher_id,
        TimetableSlot.period_definition_id == period_definition_id,
        TimetableSlot.day_of_week == day_of_week,
        TimetableSlot.status == TimetableSlotStatus.ACTIVE,
        # Overlap: existing.effective_from <= new.effective_to (or new has no end)
        # AND (existing.effective_to IS NULL OR existing.effective_to >= new.effective_from)
        or_(
            effective_to is None,
            TimetableSlot.effective_from <= effective_to,
        ),
        or_(
            TimetableSlot.effective_to.is_(None),
            TimetableSlot.effective_to >= effective_from,
        ),
    )
    if exclude_id:
        stmt = stmt.where(TimetableSlot.id != exclude_id)
    result = (await session.scalars(stmt)).first()
    return result is not None


async def check_cohort_conflict(
    session: AsyncSession,
    cohort_id: str,
    period_definition_id: str,
    day_of_week: str,
    effective_from: date,
    effective_to: date | None,
    *,
    exclude_id: str | None = None,
) -> bool:
    """Return True if cohort already has an ACTIVE slot at that period+day with overlapping dates."""
    stmt = select(TimetableSlot.id).where(
        TimetableSlot.cohort_id == cohort_id,
        TimetableSlot.period_definition_id == period_definition_id,
        TimetableSlot.day_of_week == day_of_week,
        TimetableSlot.status == TimetableSlotStatus.ACTIVE,
        or_(
            effective_to is None,
            TimetableSlot.effective_from <= effective_to,
        ),
        or_(
            TimetableSlot.effective_to.is_(None),
            TimetableSlot.effective_to >= effective_from,
        ),
    )
    if exclude_id:
        stmt = stmt.where(TimetableSlot.id != exclude_id)
    result = (await session.scalars(stmt)).first()
    return result is not None


async def slot_has_no_references(session: AsyncSession, period_definition_id: str) -> bool:
    """Return True if no timetable slots reference this period definition."""
    stmt = select(TimetableSlot.id).where(
        TimetableSlot.period_definition_id == period_definition_id
    )
    result = (await session.scalars(stmt)).first()
    return result is None
