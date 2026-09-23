"""Attendance business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, StaleResourceError
from app.db.types import gen_ulid
from app.modules.attendance import repository
from app.modules.attendance.enums import AttendanceSessionStatus, AttendanceStatus
from app.modules.attendance.models import AttendanceRecord, AttendanceSession
from app.modules.attendance.schemas import (
    AttendanceRecordUpdate,
    AttendanceSessionCreate,
    AttendanceSessionUpdate,
    BulkRecordUpdate,
)
from app.modules.platform_.audit.service import audit, snapshot
from app.modules.students.enums import EnrollmentStatus
from app.modules.students.models import Student, StudentEnrollment

_SESSION_FIELDS = ["cohort_id", "academic_year_id", "session_date", "status", "notes"]
_RECORD_FIELDS = ["status", "arrived_at", "notes"]


def _session_snapshot(sess: AttendanceSession) -> dict:
    s = snapshot(sess, _SESSION_FIELDS)
    s["session_date"] = str(sess.session_date) if sess.session_date else None
    return s


async def _get_active_enrollments_for_cohort(
    session: AsyncSession, cohort_id: str, school_id: str, session_date: object
) -> list[StudentEnrollment]:
    stmt = (
        select(StudentEnrollment)
        .where(
            StudentEnrollment.cohort_id == cohort_id,
            StudentEnrollment.school_id == school_id,
            StudentEnrollment.status == EnrollmentStatus.ACTIVE.value,
        )
    )
    # Filter by date range if provided
    from datetime import date as _date
    if isinstance(session_date, _date):
        stmt = stmt.where(
            StudentEnrollment.start_date <= session_date,
        )
    return list((await session.scalars(stmt)).all())


async def create_session(
    session: AsyncSession, ctx: RequestContext, payload: AttendanceSessionCreate
) -> AttendanceSession:
    if ctx.school_id is None:
        raise ForbiddenError("No school context set.")

    existing = await repository.get_session_for_cohort_date(
        session, payload.cohort_id, payload.session_date, ctx.school_id
    )
    if existing is not None:
        raise ConflictError(
            "An attendance session already exists for this cohort on this date.",
            code="SESSION_ALREADY_EXISTS",
            details={"cohort_id": payload.cohort_id, "session_date": str(payload.session_date)},
        )

    attendance_session = AttendanceSession(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        cohort_id=payload.cohort_id,
        academic_year_id=payload.academic_year_id,
        session_date=payload.session_date,
        notes=payload.notes,
        created_by_id=ctx.user_id,
        updated_by_id=ctx.user_id,
    )
    session.add(attendance_session)
    await session.flush()

    # Auto-create records for each active enrollment
    enrollments = await _get_active_enrollments_for_cohort(
        session, payload.cohort_id, ctx.school_id, payload.session_date
    )
    for enrollment in enrollments:
        record = AttendanceRecord(
            school_id=ctx.school_id,
            organization_id=ctx.organization_id,
            session_id=attendance_session.id,
            enrollment_id=enrollment.id,
            student_id=enrollment.student_id,
            status=AttendanceStatus.PRESENT.value,
            created_by_id=ctx.user_id,
            updated_by_id=ctx.user_id,
        )
        session.add(record)
    await session.flush()

    await audit(
        session, ctx,
        action="ATTENDANCE_SESSION_CREATED",
        entity_type="attendance_session",
        entity_id=attendance_session.id,
        summary=f"Attendance session created for cohort {payload.cohort_id} on {payload.session_date}",
        after=_session_snapshot(attendance_session),
    )
    return attendance_session


async def update_session(
    session: AsyncSession, ctx: RequestContext, session_id: str, payload: AttendanceSessionUpdate
) -> AttendanceSession:
    attendance_session = await _get_owned_session(session, ctx, session_id)

    if attendance_session.status != AttendanceSessionStatus.DRAFT.value:
        raise ForbiddenError(
            "Only DRAFT sessions can be updated.",
            code="SESSION_NOT_EDITABLE",
        )

    if attendance_session.version != payload.version:
        raise StaleResourceError()

    before = _session_snapshot(attendance_session)
    update_data = payload.model_dump(exclude={"version"}, exclude_none=True)
    for field, value in update_data.items():
        setattr(attendance_session, field, value)
    attendance_session.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ATTENDANCE_SESSION_UPDATED",
        entity_type="attendance_session",
        entity_id=attendance_session.id,
        summary=f"Attendance session {session_id} updated",
        before=before,
        after=_session_snapshot(attendance_session),
    )
    return attendance_session


async def delete_session(
    session: AsyncSession, ctx: RequestContext, session_id: str, version: int
) -> None:
    attendance_session = await _get_owned_session(session, ctx, session_id)

    if attendance_session.status != AttendanceSessionStatus.DRAFT.value:
        raise ForbiddenError(
            "Only DRAFT sessions can be deleted.",
            code="SESSION_NOT_DELETABLE",
        )

    if attendance_session.version != version:
        raise StaleResourceError()

    before = _session_snapshot(attendance_session)
    await session.delete(attendance_session)
    await session.flush()

    await audit(
        session, ctx,
        action="ATTENDANCE_SESSION_DELETED",
        entity_type="attendance_session",
        entity_id=session_id,
        summary=f"Attendance session {session_id} deleted",
        before=before,
    )


async def submit_session(
    session: AsyncSession, ctx: RequestContext, session_id: str, version: int
) -> AttendanceSession:
    attendance_session = await _get_owned_session(session, ctx, session_id)

    if attendance_session.status != AttendanceSessionStatus.DRAFT.value:
        raise ForbiddenError(
            "Only DRAFT sessions can be submitted.",
            code="SESSION_NOT_SUBMITTABLE",
        )

    if attendance_session.version != version:
        raise StaleResourceError()

    before = _session_snapshot(attendance_session)
    attendance_session.status = AttendanceSessionStatus.SUBMITTED.value
    attendance_session.submitted_at = datetime.now(UTC)
    attendance_session.submitted_by_id = ctx.user_id
    attendance_session.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ATTENDANCE_SESSION_SUBMITTED",
        entity_type="attendance_session",
        entity_id=attendance_session.id,
        summary=f"Attendance session {session_id} submitted",
        before=before,
        after=_session_snapshot(attendance_session),
    )
    return attendance_session


async def amend_session(
    session: AsyncSession, ctx: RequestContext, session_id: str, version: int
) -> AttendanceSession:
    attendance_session = await _get_owned_session(session, ctx, session_id)

    if attendance_session.status not in (
        AttendanceSessionStatus.SUBMITTED.value,
        AttendanceSessionStatus.AMENDED.value,
    ):
        raise ForbiddenError(
            "Only SUBMITTED or AMENDED sessions can be amended.",
            code="SESSION_NOT_AMENDABLE",
        )

    if attendance_session.version != version:
        raise StaleResourceError()

    before = _session_snapshot(attendance_session)
    attendance_session.status = AttendanceSessionStatus.AMENDED.value
    attendance_session.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ATTENDANCE_SESSION_AMENDED",
        entity_type="attendance_session",
        entity_id=attendance_session.id,
        summary=f"Attendance session {session_id} amended",
        before=before,
        after=_session_snapshot(attendance_session),
    )
    return attendance_session


async def update_record(
    session: AsyncSession, ctx: RequestContext, record_id: str, payload: AttendanceRecordUpdate
) -> AttendanceRecord:
    if ctx.school_id is None:
        raise ForbiddenError("No school context set.")

    record = await repository.get_record(session, record_id, ctx.school_id)
    if record is None:
        raise NotFoundError("The attendance record was not found.", code="ATTENDANCE_RECORD_NOT_FOUND")

    # Load parent session to check status
    parent_session = await repository.get_session_by_id(session, record.session_id, ctx.school_id)
    if parent_session is None:
        raise NotFoundError("The attendance session was not found.", code="ATTENDANCE_SESSION_NOT_FOUND")

    if parent_session.status == AttendanceSessionStatus.SUBMITTED.value:
        raise ForbiddenError(
            "Records cannot be modified while the session is SUBMITTED. Amend the session first.",
            code="SESSION_SUBMITTED",
        )

    before = snapshot(record, _RECORD_FIELDS)
    record.status = payload.status.value
    record.arrived_at = payload.arrived_at
    record.notes = payload.notes
    record.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ATTENDANCE_RECORD_UPDATED",
        entity_type="attendance_record",
        entity_id=record.id,
        summary=f"Attendance record {record_id} updated",
        before=before,
        after=snapshot(record, _RECORD_FIELDS),
    )
    return record


async def bulk_update_records(
    session: AsyncSession, ctx: RequestContext, session_id: str, payload: BulkRecordUpdate
) -> None:
    if ctx.school_id is None:
        raise ForbiddenError("No school context set.")

    attendance_session = await _get_owned_session(session, ctx, session_id)

    if attendance_session.status == AttendanceSessionStatus.SUBMITTED.value:
        raise ForbiddenError(
            "Records cannot be modified while the session is SUBMITTED. Amend the session first.",
            code="SESSION_SUBMITTED",
        )

    records_data = [
        {
            "enrollment_id": item.enrollment_id,
            "status": item.status.value,
            "arrived_at": item.arrived_at,
            "notes": item.notes,
            "organization_id": ctx.organization_id,
            "student_id": await _resolve_student_id(session, item.enrollment_id, ctx.school_id),
            "updated_by_id": ctx.user_id,
            "created_by_id": ctx.user_id,
        }
        for item in payload.records
    ]

    await repository.bulk_upsert_records(session, session_id, records_data, ctx.school_id)
    await session.flush()

    await audit(
        session, ctx,
        action="ATTENDANCE_SESSION_BULK_UPDATED",
        entity_type="attendance_session",
        entity_id=session_id,
        summary=f"Bulk update of {len(payload.records)} attendance records for session {session_id}",
    )


async def _resolve_student_id(
    session: AsyncSession, enrollment_id: str, school_id: str
) -> str:
    """Resolve student_id from enrollment_id."""
    from app.modules.students.models import StudentEnrollment
    stmt = select(StudentEnrollment.student_id).where(
        StudentEnrollment.id == enrollment_id,
        StudentEnrollment.school_id == school_id,
    )
    result = await session.scalar(stmt)
    return result or ""


async def _get_owned_session(
    session: AsyncSession, ctx: RequestContext, session_id: str
) -> AttendanceSession:
    if ctx.school_id is None:
        raise NotFoundError("The attendance session was not found.", code="ATTENDANCE_SESSION_NOT_FOUND")
    obj = await repository.get_session_by_id(session, session_id, ctx.school_id)
    if obj is None:
        raise NotFoundError("The attendance session was not found.", code="ATTENDANCE_SESSION_NOT_FOUND")
    return obj
