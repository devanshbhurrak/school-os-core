"""Timetable routes — period definitions and slots."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.timetables import repository, service
from app.modules.timetables.models import TimetableSlot
from app.modules.timetables.permissions import (
    PERIOD_CREATE,
    PERIOD_DELETE,
    PERIOD_LIST,
    PERIOD_READ,
    PERIOD_UPDATE,
    SLOT_CREATE,
    SLOT_DELETE,
    SLOT_LIST,
    SLOT_READ,
    SLOT_UPDATE,
)
from app.modules.timetables.schemas import (
    PeriodDefinitionCreate,
    PeriodDefinitionRead,
    PeriodDefinitionUpdate,
    TimetableSlotCreate,
    TimetableSlotRead,
    TimetableSlotUpdate,
)

router = APIRouter(tags=["timetables"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _slot_read(slot: TimetableSlot) -> TimetableSlotRead:
    """Build TimetableSlotRead with denormalized display fields."""
    teacher_name: str | None = None
    try:
        person = slot.teacher.person
        teacher_name = " ".join(
            p for p in [person.first_name, person.last_name] if p
        ) or None
    except Exception:
        pass

    subject_name: str | None = None
    try:
        subject_name = slot.subject.name
    except Exception:
        pass

    cohort_name: str | None = None
    try:
        cohort_name = slot.cohort.name
    except Exception:
        pass

    period_name: str | None = None
    try:
        period_name = slot.period_definition.name
    except Exception:
        pass

    data = {
        "id": slot.id,
        "school_id": slot.school_id,
        "organization_id": slot.organization_id,
        "academic_year_id": slot.academic_year_id,
        "cohort_id": slot.cohort_id,
        "period_definition_id": slot.period_definition_id,
        "teacher_id": slot.teacher_id,
        "subject_id": slot.subject_id,
        "day_of_week": slot.day_of_week,
        "effective_from": slot.effective_from,
        "effective_to": slot.effective_to,
        "status": slot.status,
        "notes": slot.notes,
        "version": slot.version,
        "created_at": slot.created_at,
        "updated_at": slot.updated_at,
        "teacher_name": teacher_name,
        "subject_name": subject_name,
        "cohort_name": cohort_name,
        "period_name": period_name,
    }
    return TimetableSlotRead.model_validate(data)


# ---------------------------------------------------------------------------
# Period Definitions
# ---------------------------------------------------------------------------


@router.get("/period-definitions", response_model=CursorPage[PeriodDefinitionRead])
async def list_period_definitions(
    academic_year_id: str = Query(...),
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(PERIOD_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)
    page = await repository.list_for_year(
        session, ctx.school_id, academic_year_id,
        cursor=params.cursor, limit=params.limit,
    )
    return page


@router.get("/period-definitions/{period_id}", response_model=PeriodDefinitionRead)
async def get_period_definition(
    period_id: str,
    ctx: RequestContext = Depends(require(PERIOD_READ)),
    session: SessionDep = None,
):
    return await service.get_period_owned(session, ctx, period_id)


@router.post("/period-definitions", response_model=PeriodDefinitionRead, status_code=status.HTTP_201_CREATED)
async def create_period_definition(
    data: PeriodDefinitionCreate,
    ctx: RequestContext = Depends(require(PERIOD_CREATE)),
    session: SessionDep = None,
):
    return await service.create_period(session, ctx, data)


@router.patch("/period-definitions/{period_id}", response_model=PeriodDefinitionRead)
async def update_period_definition(
    period_id: str,
    data: PeriodDefinitionUpdate,
    ctx: RequestContext = Depends(require(PERIOD_UPDATE)),
    session: SessionDep = None,
):
    period = await service.get_period_owned(session, ctx, period_id)
    return await service.update_period(session, ctx, period, data)


@router.delete("/period-definitions/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_period_definition(
    period_id: str,
    ctx: RequestContext = Depends(require(PERIOD_DELETE)),
    session: SessionDep = None,
):
    period = await service.get_period_owned(session, ctx, period_id)
    await service.delete_period(session, ctx, period)


# ---------------------------------------------------------------------------
# Timetable Slots
# ---------------------------------------------------------------------------


@router.get("/timetable-slots", response_model=CursorPage[TimetableSlotRead])
async def list_timetable_slots(
    cohort_id: str | None = Query(default=None),
    academic_year_id: str | None = Query(default=None),
    day_of_week: str | None = Query(default=None),
    teacher_id: str | None = Query(default=None),
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(SLOT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)

    if cohort_id:
        page = await repository.list_for_cohort(
            session, cohort_id, ctx.school_id,
            academic_year_id=academic_year_id,
            day_of_week=day_of_week,
            cursor=params.cursor,
            limit=params.limit,
        )
    elif teacher_id:
        page = await repository.list_for_teacher(
            session, teacher_id, ctx.school_id,
            academic_year_id=academic_year_id,
            day_of_week=day_of_week,
            cursor=params.cursor,
            limit=params.limit,
        )
    else:
        # Return empty if no filter provided
        return CursorPage(items=[], next_cursor=None, has_more=False)

    # Load related objects for each slot
    items = []
    for slot in page.items:
        loaded = await repository.get_slot_by_id(session, ctx.school_id, slot.id)
        if loaded:
            items.append(await _slot_read(loaded))
    return CursorPage(items=items, next_cursor=page.next_cursor, has_more=page.has_more)


@router.get("/timetable-slots/{slot_id}", response_model=TimetableSlotRead)
async def get_timetable_slot(
    slot_id: str,
    ctx: RequestContext = Depends(require(SLOT_READ)),
    session: SessionDep = None,
):
    slot = await service.get_slot_owned(session, ctx, slot_id)
    return await _slot_read(slot)


@router.post("/timetable-slots", response_model=TimetableSlotRead, status_code=status.HTTP_201_CREATED)
async def create_timetable_slot(
    data: TimetableSlotCreate,
    ctx: RequestContext = Depends(require(SLOT_CREATE)),
    session: SessionDep = None,
):
    slot = await service.create_slot(session, ctx, data)
    loaded = await repository.get_slot_by_id(session, ctx.school_id, slot.id)
    return await _slot_read(loaded)


@router.patch("/timetable-slots/{slot_id}", response_model=TimetableSlotRead)
async def update_timetable_slot(
    slot_id: str,
    data: TimetableSlotUpdate,
    ctx: RequestContext = Depends(require(SLOT_UPDATE)),
    session: SessionDep = None,
):
    slot = await service.get_slot_owned(session, ctx, slot_id)
    updated = await service.update_slot(session, ctx, slot, data)
    loaded = await repository.get_slot_by_id(session, ctx.school_id, updated.id)
    return await _slot_read(loaded)


@router.delete("/timetable-slots/{slot_id}", response_model=TimetableSlotRead)
async def cancel_timetable_slot(
    slot_id: str,
    ctx: RequestContext = Depends(require(SLOT_DELETE)),
    session: SessionDep = None,
):
    slot = await service.get_slot_owned(session, ctx, slot_id)
    cancelled = await service.delete_slot(session, ctx, slot)
    loaded = await repository.get_slot_by_id(session, ctx.school_id, cancelled.id)
    return await _slot_read(loaded)
