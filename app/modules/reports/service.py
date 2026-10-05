"""Report / CSV export business logic."""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import RequestContext
from app.core.errors import InvalidRequestError, NotFoundError
from app.modules.attendance.models import AttendanceRecord, AttendanceSession
from app.modules.people.models import Person
from app.modules.reports import repository
from app.modules.reports.enums import ExportJobStatus, ReportType
from app.modules.reports.models import ExportJob
from app.modules.reports.schemas import ExportRequest
from app.modules.students.models import Student, StudentEnrollment
from app.modules.teachers.models import Teacher
from app.modules.platform_.audit.service import audit


def _generate_csv(headers: list[str], rows: list[list]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


async def generate_student_csv(session: AsyncSession, ctx: RequestContext, filters: dict | None) -> tuple[bytes, int]:
    stmt = (
        select(Student)
        .options(selectinload(Student.person))
        .where(
            Student.school_id == ctx.school_id,
            Student.deleted_at.is_(None),
        )
    )
    result = (await session.scalars(stmt)).all()
    headers = ["id", "admission_number", "status", "admission_date", "first_name", "last_name", "primary_email", "primary_phone"]
    rows = []
    for s in result:
        p = s.person
        rows.append([
            s.id, s.admission_number, s.status, str(s.admission_date),
            getattr(p, "first_name", ""), getattr(p, "last_name", ""),
            getattr(p, "primary_email", ""), getattr(p, "primary_phone", ""),
        ])
    return _generate_csv(headers, rows), len(rows)


async def generate_teacher_csv(session: AsyncSession, ctx: RequestContext, filters: dict | None) -> tuple[bytes, int]:
    stmt = (
        select(Teacher)
        .options(selectinload(Teacher.person))
        .where(
            Teacher.school_id == ctx.school_id,
            Teacher.deleted_at.is_(None),
        )
    )
    result = (await session.scalars(stmt)).all()
    headers = ["id", "employee_number", "designation", "status", "joining_date", "first_name", "last_name", "primary_email", "primary_phone"]
    rows = []
    for t in result:
        p = t.person
        rows.append([
            t.id, t.employee_number or "", t.designation or "", t.status,
            str(t.joining_date) if t.joining_date else "",
            getattr(p, "first_name", ""), getattr(p, "last_name", ""),
            getattr(p, "primary_email", ""), getattr(p, "primary_phone", ""),
        ])
    return _generate_csv(headers, rows), len(rows)


async def generate_attendance_summary_csv(session: AsyncSession, ctx: RequestContext, filters: dict | None) -> tuple[bytes, int]:
    stmt = (
        select(
            AttendanceRecord.student_id,
            func.count().label("total_records"),
            func.count().filter(AttendanceRecord.status == "PRESENT").label("present_count"),
            func.count().filter(AttendanceRecord.status == "ABSENT").label("absent_count"),
            func.count().filter(AttendanceRecord.status == "LATE").label("late_count"),
        )
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .where(AttendanceSession.school_id == ctx.school_id)
        .group_by(AttendanceRecord.student_id)
    )
    result = (await session.execute(stmt)).all()
    headers = ["student_id", "total_records", "present", "absent", "late"]
    rows = [[r.student_id, r.total_records, r.present_count, r.absent_count, r.late_count] for r in result]
    return _generate_csv(headers, rows), len(rows)


async def generate_enrollment_csv(session: AsyncSession, ctx: RequestContext, filters: dict | None) -> tuple[bytes, int]:
    stmt = (
        select(StudentEnrollment)
        .where(StudentEnrollment.school_id == ctx.school_id)
    )
    result = (await session.scalars(stmt)).all()
    headers = ["id", "student_id", "academic_year_id", "cohort_id", "roll_number", "start_date", "end_date", "enrollment_type", "status"]
    rows = []
    for e in result:
        rows.append([
            e.id, e.student_id, e.academic_year_id, e.cohort_id,
            e.roll_number or "", str(e.start_date),
            str(e.end_date) if e.end_date else "",
            e.enrollment_type, e.status,
        ])
    return _generate_csv(headers, rows), len(rows)


_GENERATORS = {
    ReportType.STUDENTS: generate_student_csv,
    ReportType.TEACHERS: generate_teacher_csv,
    ReportType.ATTENDANCE_SUMMARY: generate_attendance_summary_csv,
    ReportType.ENROLLMENTS: generate_enrollment_csv,
}


async def request_export(
    session: AsyncSession,
    ctx: RequestContext,
    payload: ExportRequest,
) -> tuple[ExportJob, bytes | None]:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    report_type = payload.report_type
    if report_type not in ReportType.__members__:
        raise InvalidRequestError(f"Unsupported report type: {report_type}")

    job = ExportJob(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        report_type=report_type,
        status=ExportJobStatus.PENDING,
        filters=payload.filters,
        created_by_id=ctx.user_id,
    )
    await repository.create_job(session, job)

    # Synchronous generation for small datasets
    csv_bytes: bytes | None = None
    try:
        generator = _GENERATORS[ReportType(report_type)]
        job.started_at = datetime.now(UTC)
        job.status = ExportJobStatus.PROCESSING
        csv_data, row_count = await generator(session, ctx, payload.filters)
        job.status = ExportJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        job.row_count = row_count
        csv_bytes = csv_data
    except Exception as exc:
        job.status = ExportJobStatus.FAILED
        job.error_message = str(exc)[:2000]
        job.completed_at = datetime.now(UTC)

    await session.flush()

    await audit(
        session, ctx,
        action="REPORT_EXPORTED",
        entity_type="export_job",
        entity_id=job.id,
        summary=f"Export {job.report_type} requested (status={job.status})",
    )
    return job, csv_bytes


async def get_job(session: AsyncSession, ctx: RequestContext, job_id: str) -> ExportJob:
    if ctx.school_id is None:
        raise NotFoundError("Export job not found.", code="EXPORT_JOB_NOT_FOUND")
    job = await repository.get_by_id(session, job_id, ctx.school_id)
    if job is None:
        raise NotFoundError("Export job not found.", code="EXPORT_JOB_NOT_FOUND")
    return job


async def get_download(
    session: AsyncSession,
    ctx: RequestContext,
    job_id: str,
) -> tuple[ExportJob, bytes]:
    """Re-generate CSV for a completed job (small export path)."""
    job = await get_job(session, ctx, job_id)
    if job.status != ExportJobStatus.COMPLETED:
        raise InvalidRequestError("Export job is not yet completed.")

    generator = _GENERATORS.get(ReportType(job.report_type))
    if generator is None:
        raise InvalidRequestError(f"Unsupported report type: {job.report_type}")

    csv_data, _ = await generator(session, ctx, job.filters)
    return job, csv_data
