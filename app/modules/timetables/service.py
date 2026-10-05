"""Timetable business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.timetables import repository
from app.modules.timetables.enums import TimetableSlotStatus, TimetableStatus
from app.modules.timetables.models import PeriodDefinition, Timetable, TimetableSlot
from app.modules.timetables.schemas import (
    ConflictItem,
    PeriodDefinitionCreate,
    PeriodDefinitionUpdate,
    PublishResult,
    TimetableCreate,
    TimetableUpdate,
    TimetableSlotCreate,
    TimetableSlotUpdate,
)
from app.modules.platform_.audit.service import audit, snapshot

_TIMETABLE_FIELDS = ["name", "status", "published_at", "archived_at"]
_PERIOD_FIELDS = ["name", "period_type", "sort_order"]
_SLOT_FIELDS = ["teacher_id", "subject_id", "day_of_week", "effective_from", "effective_to", "status"]


def _period_snapshot(period: PeriodDefinition) -> dict:
    s = snapshot(period, _PERIOD_FIELDS)
    s["start_time"] = str(period.start_time) if period.start_time else None
    s["end_time"] = str(period.end_time) if period.end_time else None
    return s


def _slot_snapshot(slot: TimetableSlot) -> dict:
    s = snapshot(slot, _SLOT_FIELDS)
    s["effective_from"] = str(slot.effective_from) if slot.effective_from else None
    s["effective_to"] = str(slot.effective_to) if slot.effective_to else None
    return s


def _timetable_snapshot(tt: Timetable) -> dict:
    s = snapshot(tt, _TIMETABLE_FIELDS)
    s["published_at"] = str(tt.published_at) if tt.published_at else None
    s["archived_at"] = str(tt.archived_at) if tt.archived_at else None
    return s


# ---------------------------------------------------------------------------
# Timetable Header
# ---------------------------------------------------------------------------


async def create_timetable(
    session: AsyncSession, ctx: RequestContext, data: TimetableCreate
) -> Timetable:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    instance = Timetable(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        academic_year_id=data.academic_year_id,
        name=data.name,
        status=TimetableStatus.DRAFT,
        created_by_id=ctx.user_id,
    )
    await repository.create_timetable(session, instance)

    await audit(
        session, ctx,
        action="TIMETABLE_CREATED",
        entity_type="timetable",
        entity_id=instance.id,
        summary=f"Timetable {instance.name!r} created",
        after=_timetable_snapshot(instance),
    )
    return instance


async def update_timetable(
    session: AsyncSession, ctx: RequestContext, timetable_id: str, data: TimetableUpdate
) -> Timetable:
    if ctx.school_id is None:
        raise NotFoundError("The timetable was not found.", code="TIMETABLE_NOT_FOUND")

    tt = await repository.get_timetable(session, timetable_id, ctx.school_id)
    if tt is None:
        raise NotFoundError("The timetable was not found.", code="TIMETABLE_NOT_FOUND")

    if tt.status != TimetableStatus.DRAFT:
        raise InvalidRequestError(
            "Only DRAFT timetables can be updated.",
            code="TIMETABLE_NOT_DRAFT",
        )

    if tt.version != data.version:
        raise StaleResourceError()

    before = _timetable_snapshot(tt)
    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    for field, value in payload.items():
        setattr(tt, field, value)
    tt.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TIMETABLE_UPDATED",
        entity_type="timetable",
        entity_id=tt.id,
        summary=f"Timetable {tt.name!r} updated",
        before=before,
        after=_timetable_snapshot(tt),
    )
    return tt


async def publish_timetable(
    session: AsyncSession, ctx: RequestContext, timetable_id: str, version: int
) -> PublishResult:
    if ctx.school_id is None:
        raise NotFoundError("The timetable was not found.", code="TIMETABLE_NOT_FOUND")

    tt = await repository.get_timetable(session, timetable_id, ctx.school_id)
    if tt is None:
        raise NotFoundError("The timetable was not found.", code="TIMETABLE_NOT_FOUND")

    if tt.status != TimetableStatus.DRAFT:
        raise InvalidRequestError(
            "Only DRAFT timetables can be published.",
            code="TIMETABLE_NOT_DRAFT",
        )

    if tt.version != version:
        raise StaleResourceError()

    # Run conflict detection
    raw_conflicts = await repository.find_conflicts(session, timetable_id, ctx.school_id)
    if raw_conflicts:
        conflicts = [ConflictItem(**c) for c in raw_conflicts]
        return PublishResult(success=False, conflicts=conflicts)

    before = _timetable_snapshot(tt)

    # Archive any other PUBLISHED timetable for same school+year
    existing = await repository.get_published_timetable_for_year(
        session, ctx.school_id, tt.academic_year_id, exclude_id=tt.id
    )
    if existing:
        old_before = _timetable_snapshot(existing)
        existing.status = TimetableStatus.ARCHIVED
        existing.archived_at = datetime.now(UTC)
        existing.updated_by_id = ctx.user_id
        await session.flush()
        await audit(
            session, ctx,
            action="TIMETABLE_ARCHIVED",
            entity_type="timetable",
            entity_id=existing.id,
            summary=f"Timetable {existing.name!r} auto-archived (replaced by {tt.name!r})",
            before=old_before,
            after=_timetable_snapshot(existing),
        )

    tt.status = TimetableStatus.PUBLISHED
    tt.published_at = datetime.now(UTC)
    tt.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TIMETABLE_PUBLISHED",
        entity_type="timetable",
        entity_id=tt.id,
        summary=f"Timetable {tt.name!r} published",
        before=before,
        after=_timetable_snapshot(tt),
    )
    return PublishResult(success=True)


async def archive_timetable(
    session: AsyncSession, ctx: RequestContext, timetable_id: str, version: int
) -> Timetable:
    if ctx.school_id is None:
        raise NotFoundError("The timetable was not found.", code="TIMETABLE_NOT_FOUND")

    tt = await repository.get_timetable(session, timetable_id, ctx.school_id)
    if tt is None:
        raise NotFoundError("The timetable was not found.", code="TIMETABLE_NOT_FOUND")

    if tt.status == TimetableStatus.ARCHIVED:
        raise InvalidRequestError(
            "This timetable is already archived.",
            code="TIMETABLE_ALREADY_ARCHIVED",
        )

    if tt.version != version:
        raise StaleResourceError()

    before = _timetable_snapshot(tt)
    tt.status = TimetableStatus.ARCHIVED
    tt.archived_at = datetime.now(UTC)
    tt.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TIMETABLE_ARCHIVED",
        entity_type="timetable",
        entity_id=tt.id,
        summary=f"Timetable {tt.name!r} archived",
        before=before,
        after=_timetable_snapshot(tt),
    )
    return tt


async def get_timetable_owned(
    session: AsyncSession, ctx: RequestContext, timetable_id: str
) -> Timetable:
    if ctx.school_id is None:
        raise NotFoundError("The timetable was not found.", code="TIMETABLE_NOT_FOUND")
    obj = await repository.get_timetable(session, timetable_id, ctx.school_id)
    if obj is None:
        raise NotFoundError("The timetable was not found.", code="TIMETABLE_NOT_FOUND")
    return obj


# ---------------------------------------------------------------------------
# Period Definitions
# ---------------------------------------------------------------------------


async def create_period(
    session: AsyncSession, ctx: RequestContext, data: PeriodDefinitionCreate
) -> PeriodDefinition:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    existing = await repository.get_period_by_name(
        session, ctx.school_id, data.academic_year_id, data.name
    )
    if existing:
        raise ConflictError(
            f"A period definition named {data.name!r} already exists for this academic year.",
            code="PERIOD_NAME_TAKEN",
            details={"name": data.name},
        )

    instance = PeriodDefinition(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="PERIOD_DEFINITION_CREATED",
        entity_type="period_definition",
        entity_id=instance.id,
        summary=f"Period definition {instance.name!r} created",
        after=_period_snapshot(instance),
    )
    return instance


async def update_period(
    session: AsyncSession,
    ctx: RequestContext,
    period: PeriodDefinition,
    data: PeriodDefinitionUpdate,
) -> PeriodDefinition:
    before = _period_snapshot(period)
    payload = data.model_dump(exclude_none=True)
    for field, value in payload.items():
        setattr(period, field, value)
    period.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="PERIOD_DEFINITION_UPDATED",
        entity_type="period_definition",
        entity_id=period.id,
        summary=f"Period definition {period.name!r} updated",
        before=before,
        after=_period_snapshot(period),
    )
    return period


async def delete_period(
    session: AsyncSession, ctx: RequestContext, period: PeriodDefinition
) -> None:
    if not await repository.slot_has_no_references(session, period.id):
        raise ConflictError(
            "Cannot delete a period definition that has timetable slots referencing it.",
            code="PERIOD_HAS_SLOTS",
            details={"period_definition_id": period.id},
        )

    before = _period_snapshot(period)
    await session.delete(period)
    await session.flush()

    await audit(
        session, ctx,
        action="PERIOD_DEFINITION_DELETED",
        entity_type="period_definition",
        entity_id=period.id,
        summary=f"Period definition {period.name!r} deleted",
        before=before,
    )


async def get_period_owned(
    session: AsyncSession, ctx: RequestContext, period_id: str
) -> PeriodDefinition:
    if ctx.school_id is None:
        raise NotFoundError("The period definition was not found.", code="PERIOD_NOT_FOUND")
    obj = await repository.get_period_by_id(session, ctx.school_id, period_id)
    if obj is None:
        raise NotFoundError("The period definition was not found.", code="PERIOD_NOT_FOUND")
    return obj


# ---------------------------------------------------------------------------
# Timetable Slots
# ---------------------------------------------------------------------------


async def create_slot(
    session: AsyncSession, ctx: RequestContext, data: TimetableSlotCreate
) -> TimetableSlot:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Check teacher conflict
    if await repository.check_teacher_conflict(
        session,
        data.teacher_id,
        data.period_definition_id,
        data.day_of_week,
        data.effective_from,
        data.effective_to,
    ):
        raise ConflictError(
            "This teacher already has an active slot at this period and day.",
            code="TEACHER_CONFLICT",
            details={
                "teacher_id": data.teacher_id,
                "period_definition_id": data.period_definition_id,
                "day_of_week": data.day_of_week,
            },
        )

    # Check cohort conflict
    if await repository.check_cohort_conflict(
        session,
        data.cohort_id,
        data.period_definition_id,
        data.day_of_week,
        data.effective_from,
        data.effective_to,
    ):
        raise ConflictError(
            "This cohort already has an active slot at this period and day.",
            code="COHORT_CONFLICT",
            details={
                "cohort_id": data.cohort_id,
                "period_definition_id": data.period_definition_id,
                "day_of_week": data.day_of_week,
            },
        )

    # Fetch the academic_year_id from the period definition
    period = await repository.get_period_by_id(session, ctx.school_id, data.period_definition_id)
    if period is None:
        raise NotFoundError("The period definition was not found.", code="PERIOD_NOT_FOUND")

    # Cross-school validation
    if data.teacher_id:
        from app.modules.teachers.models import Teacher
        teacher = await session.get(Teacher, data.teacher_id)
        if teacher is None or teacher.school_id != ctx.school_id:
            raise InvalidRequestError(
                "The teacher does not belong to this school.",
                code="TEACHER_SCHOOL_MISMATCH",
            )

    if data.subject_id:
        from app.modules.academic.models import Subject
        subject = await session.get(Subject, data.subject_id)
        if subject is None or subject.school_id != ctx.school_id:
            raise InvalidRequestError(
                "The subject does not belong to this school.",
                code="SUBJECT_SCHOOL_MISMATCH",
            )

    instance = TimetableSlot(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        academic_year_id=period.academic_year_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="TIMETABLE_SLOT_CREATED",
        entity_type="timetable_slot",
        entity_id=instance.id,
        summary="Timetable slot created",
        after=_slot_snapshot(instance),
    )
    return instance


async def update_slot(
    session: AsyncSession,
    ctx: RequestContext,
    slot: TimetableSlot,
    data: TimetableSlotUpdate,
) -> TimetableSlot:
    if slot.version != data.version:
        raise StaleResourceError()

    before = _slot_snapshot(slot)
    payload = data.model_dump(exclude={"version"}, exclude_none=True)

    # Check conflicts if teacher, period, or day are changing
    teacher_id = payload.get("teacher_id", slot.teacher_id)
    period_definition_id = slot.period_definition_id
    day_of_week = slot.day_of_week
    effective_from = payload.get("effective_from", slot.effective_from)
    effective_to = payload.get("effective_to", slot.effective_to)

    if "teacher_id" in payload:
        if await repository.check_teacher_conflict(
            session, teacher_id, period_definition_id, day_of_week,
            effective_from, effective_to, exclude_id=slot.id
        ):
            raise ConflictError(
                "This teacher already has an active slot at this period and day.",
                code="TEACHER_CONFLICT",
                details={"teacher_id": teacher_id},
            )

    # Check cohort conflict
    cohort_id = payload.get("cohort_id", slot.cohort_id)
    if await repository.check_cohort_conflict(
        session, cohort_id, period_definition_id, day_of_week,
        effective_from, effective_to, exclude_id=slot.id
    ):
        raise ConflictError(
            "This cohort already has an active slot at this period and day.",
            code="COHORT_CONFLICT",
            details={"cohort_id": cohort_id},
        )

    for field, value in payload.items():
        setattr(slot, field, value)
    slot.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TIMETABLE_SLOT_UPDATED",
        entity_type="timetable_slot",
        entity_id=slot.id,
        summary="Timetable slot updated",
        before=before,
        after=_slot_snapshot(slot),
    )
    return slot


async def delete_slot(
    session: AsyncSession, ctx: RequestContext, slot: TimetableSlot
) -> TimetableSlot:
    """Soft-cancel: set status=CANCELLED and effective_to=today."""
    before = _slot_snapshot(slot)
    slot.status = TimetableSlotStatus.CANCELLED
    slot.effective_to = datetime.now(UTC).date()
    slot.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TIMETABLE_SLOT_CANCELLED",
        entity_type="timetable_slot",
        entity_id=slot.id,
        summary="Timetable slot cancelled",
        before=before,
        after=_slot_snapshot(slot),
    )
    return slot


async def get_slot_owned(
    session: AsyncSession, ctx: RequestContext, slot_id: str
) -> TimetableSlot:
    if ctx.school_id is None:
        raise NotFoundError("The timetable slot was not found.", code="SLOT_NOT_FOUND")
    obj = await repository.get_slot_by_id(session, ctx.school_id, slot_id)
    if obj is None:
        raise NotFoundError("The timetable slot was not found.", code="SLOT_NOT_FOUND")
    return obj
