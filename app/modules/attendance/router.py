"""Attendance routes."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.attendance import repository, service
from app.modules.attendance.enums import AttendanceSessionStatus
from app.modules.attendance.permissions import (
    RECORD_LIST,
    RECORD_UPDATE,
    SESSION_AMEND,
    SESSION_CREATE,
    SESSION_DELETE,
    SESSION_LIST,
    SESSION_READ,
    SESSION_SUBMIT,
    SESSION_UPDATE,
)
from app.modules.attendance.schemas import (
    AttendanceRecordRead,
    AttendanceRecordUpdate,
    AttendanceSessionCreate,
    AttendanceSessionRead,
    AttendanceSessionUpdate,
    BulkRecordUpdate,
    SessionAmend,
    SessionSubmit,
)

router = APIRouter(tags=["attendance"])


class SessionDelete(BaseModel):
    version: int = Field(ge=1)


def _record_read(record: object) -> AttendanceRecordRead:
    """Build AttendanceRecordRead with denormalized student name if loaded."""
    student_name: str | None = None
    # Try to resolve student name from relationships (if loaded)
    try:
        enrollment = getattr(record, "_enrollment", None)
        if enrollment:
            student = getattr(enrollment, "student", None)
            if student:
                person = getattr(student, "person", None)
                if person:
                    first = getattr(person, "first_name", "") or ""
                    last = getattr(person, "last_name", None)
                    student_name = " ".join(filter(None, [first, last])) or None
    except Exception:
        pass

    data = AttendanceRecordRead.model_validate(record)
    data.student_name = student_name
    return data


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get("/attendance-sessions", response_model=CursorPage[AttendanceSessionRead])
async def list_attendance_sessions(
    cohort_id: str | None = Query(default=None),
    academic_year_id: str | None = Query(default=None),
    status: AttendanceSessionStatus | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(SESSION_LIST)),
    db: SessionDep = None,
):
    if ctx.school_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)
    return await repository.list_sessions(
        db, ctx.school_id, params,
        cohort_id=cohort_id,
        academic_year_id=academic_year_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/attendance-sessions/{session_id}", response_model=AttendanceSessionRead)
async def get_attendance_session(
    session_id: str,
    ctx: RequestContext = Depends(require(SESSION_READ)),
    db: SessionDep = None,
):
    # get_session_by_id already selectinloads records
    obj = await repository.get_session_by_id(db, session_id, ctx.school_id)
    if obj is None:
        from app.core.errors import NotFoundError
        raise NotFoundError("The attendance session was not found.", code="ATTENDANCE_SESSION_NOT_FOUND")
    result = AttendanceSessionRead.model_validate(obj)
    result.record_count = len(obj.records)
    return result


@router.post("/attendance-sessions", response_model=AttendanceSessionRead, status_code=status.HTTP_201_CREATED)
async def create_attendance_session(
    data: AttendanceSessionCreate,
    ctx: RequestContext = Depends(require(SESSION_CREATE)),
    db: SessionDep = None,
):
    obj = await service.create_session(db, ctx, data)
    # Re-fetch with records loaded so we can return record_count
    loaded = await repository.get_session_by_id(db, obj.id, ctx.school_id)
    result = AttendanceSessionRead.model_validate(loaded)
    result.record_count = len(loaded.records) if loaded else 0
    return result


@router.patch("/attendance-sessions/{session_id}", response_model=AttendanceSessionRead)
async def update_attendance_session(
    session_id: str,
    data: AttendanceSessionUpdate,
    ctx: RequestContext = Depends(require(SESSION_UPDATE)),
    db: SessionDep = None,
):
    return await service.update_session(db, ctx, session_id, data)


@router.delete("/attendance-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attendance_session(
    session_id: str,
    data: SessionDelete,
    ctx: RequestContext = Depends(require(SESSION_DELETE)),
    db: SessionDep = None,
):
    await service.delete_session(db, ctx, session_id, data.version)


@router.post("/attendance-sessions/{session_id}/submit", response_model=AttendanceSessionRead)
async def submit_attendance_session(
    session_id: str,
    data: SessionSubmit,
    ctx: RequestContext = Depends(require(SESSION_SUBMIT)),
    db: SessionDep = None,
):
    return await service.submit_session(db, ctx, session_id, data.version)


@router.post("/attendance-sessions/{session_id}/amend", response_model=AttendanceSessionRead)
async def amend_attendance_session(
    session_id: str,
    data: SessionAmend,
    ctx: RequestContext = Depends(require(SESSION_AMEND)),
    db: SessionDep = None,
):
    return await service.amend_session(db, ctx, session_id, data.version)


@router.get("/attendance-sessions/{session_id}/records", response_model=list[AttendanceRecordRead])
async def list_attendance_records(
    session_id: str,
    ctx: RequestContext = Depends(require(RECORD_LIST)),
    db: SessionDep = None,
):
    if ctx.school_id is None:
        return []
    records = await repository.list_records_for_session(db, session_id, ctx.school_id)
    return [AttendanceRecordRead.model_validate(r) for r in records]


@router.post("/attendance-sessions/{session_id}/bulk-update", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_update_records(
    session_id: str,
    data: BulkRecordUpdate,
    ctx: RequestContext = Depends(require(RECORD_UPDATE)),
    db: SessionDep = None,
):
    await service.bulk_update_records(db, ctx, session_id, data)


# ---------------------------------------------------------------------------
# Individual records
# ---------------------------------------------------------------------------


@router.patch("/attendance-records/{record_id}", response_model=AttendanceRecordRead)
async def update_attendance_record(
    record_id: str,
    data: AttendanceRecordUpdate,
    ctx: RequestContext = Depends(require(RECORD_UPDATE)),
    db: SessionDep = None,
):
    record = await service.update_record(db, ctx, record_id, data)
    return AttendanceRecordRead.model_validate(record)
