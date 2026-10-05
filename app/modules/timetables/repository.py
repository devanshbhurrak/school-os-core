"""Timetable data access — school-scoped."""
from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.teachers.models import Teacher
from app.modules.timetables.enums import TimetableSlotStatus, TimetableStatus
from app.modules.timetables.models import PeriodDefinition, Timetable, TimetableSlot


# ---------------------------------------------------------------------------
# Timetable Header
# ---------------------------------------------------------------------------


async def create_timetable(session: AsyncSession, timetable: Timetable) -> Timetable:
    session.add(timetable)
    await session.flush()
    return timetable


async def get_timetable(
    session: AsyncSession, timetable_id: str, school_id: str
) -> Timetable | None:
    stmt = select(Timetable).where(
        Timetable.id == timetable_id,
        Timetable.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()


async def list_timetables(
    session: AsyncSession,
    school_id: str,
    *,
    academic_year_id: str | None = None,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> CursorPage[Timetable]:
    params = CursorParams(cursor=cursor, limit=limit)
    stmt = select(Timetable).where(Timetable.school_id == school_id)
    if academic_year_id:
        stmt = stmt.where(Timetable.academic_year_id == academic_year_id)
    if status:
        stmt = stmt.where(Timetable.status == status)
    stmt = stmt.order_by(Timetable.created_at.desc(), Timetable.id)
    return await paginate_cursor(session, stmt, params, model=Timetable)


async def find_conflicts(
    session: AsyncSession, timetable_id: str, school_id: str
) -> list[dict]:
    """Find teacher and cohort conflicts within a timetable's slots."""
    # Get all active slots for this timetable
    stmt = (
        select(TimetableSlot)
        .options(
            selectinload(TimetableSlot.teacher).selectinload(Teacher.person),
            selectinload(TimetableSlot.cohort),
            selectinload(TimetableSlot.period_definition),
        )
        .where(
            TimetableSlot.timetable_id == timetable_id,
            TimetableSlot.school_id == school_id,
            TimetableSlot.status == TimetableSlotStatus.ACTIVE,
        )
    )
    result = await session.scalars(stmt)
    slots = list(result)

    conflicts: list[dict] = []

    # Check teacher conflicts: same teacher, same day, same period
    teacher_map: dict[tuple[str, str, str], list[TimetableSlot]] = {}
    for slot in slots:
        key = (slot.teacher_id, slot.day_of_week, slot.period_definition_id)
        teacher_map.setdefault(key, []).append(slot)

    for key, group in teacher_map.items():
        if len(group) > 1:
            slot = group[0]
            teacher = slot.teacher
            person = getattr(teacher, "person", None) if teacher else None
            name = ""
            if person:
                first = getattr(person, "first_name", "") or ""
                last = getattr(person, "last_name", "") or ""
                name = f"{first} {last}".strip()
            period_def = slot.period_definition
            period_name = getattr(period_def, "name", slot.period_definition_id) if period_def else slot.period_definition_id
            cohort_names = []
            for s in group:
                c = getattr(s, "cohort", None)
                cohort_names.append(getattr(c, "name", s.cohort_id) if c else s.cohort_id)
            conflicts.append({
                "conflict_type": "TEACHER",
                "day_of_week": slot.day_of_week,
                "period": period_name,
                "entity_name": name,
                "details": f"Teacher {name} is assigned to multiple sections ({', '.join(cohort_names)}) at {period_name} on {slot.day_of_week}.",
            })

    # Check cohort conflicts: same cohort, same day, same period
    cohort_map: dict[tuple[str, str, str], list[TimetableSlot]] = {}
    for slot in slots:
        key = (slot.cohort_id, slot.day_of_week, slot.period_definition_id)
        cohort_map.setdefault(key, []).append(slot)

    for key, group in cohort_map.items():
        if len(group) > 1:
            slot = group[0]
            cohort = getattr(slot, "cohort", None)
            cohort_name = getattr(cohort, "name", slot.cohort_id) if cohort else slot.cohort_id
            period_def = slot.period_definition
            period_name = getattr(period_def, "name", slot.period_definition_id) if period_def else slot.period_definition_id
            conflicts.append({
                "conflict_type": "COHORT",
                "day_of_week": slot.day_of_week,
                "period": period_name,
                "entity_name": cohort_name,
                "details": f"Section {cohort_name} has multiple slots at {period_name} on {slot.day_of_week}.",
            })

    return conflicts


async def get_published_timetable_for_year(
    session: AsyncSession, school_id: str, academic_year_id: str, *, exclude_id: str | None = None
) -> Timetable | None:
    """Find the currently PUBLISHED timetable for a school+year."""
    stmt = select(Timetable).where(
        Timetable.school_id == school_id,
        Timetable.academic_year_id == academic_year_id,
        Timetable.status == TimetableStatus.PUBLISHED,
    )
    if exclude_id:
        stmt = stmt.where(Timetable.id != exclude_id)
    return (await session.scalars(stmt)).first()


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


def _slot_options() -> list:
    """Selectin-load options for denormalized slot reads."""
    return [
        selectinload(TimetableSlot.teacher).selectinload(Teacher.person),
        selectinload(TimetableSlot.subject),
        selectinload(TimetableSlot.cohort),
        selectinload(TimetableSlot.period_definition),
    ]


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
    stmt = select(TimetableSlot).options(*_slot_options()).where(
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
    stmt = select(TimetableSlot).options(*_slot_options()).where(
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
