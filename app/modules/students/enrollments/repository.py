"""Enrollment data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.students.enums import EnrollmentStatus
from app.modules.students.models import Student, StudentEnrollment


async def get_by_id(
    session: AsyncSession, enrollment_id: str, school_id: str
) -> StudentEnrollment | None:
    stmt = (
        select(StudentEnrollment)
        .options(
            selectinload(StudentEnrollment.student).selectinload(Student.person),
            selectinload(StudentEnrollment.cohort),
            selectinload(StudentEnrollment.academic_year),
        )
        .where(
            StudentEnrollment.id == enrollment_id,
            StudentEnrollment.school_id == school_id,
        )
    )
    return (await session.scalars(stmt)).first()


async def list_enrollments(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    student_id: str | None = None,
    academic_year_id: str | None = None,
    cohort_id: str | None = None,
    status: EnrollmentStatus | None = None,
) -> CursorPage[StudentEnrollment]:
    stmt = (
        select(StudentEnrollment)
        .options(
            selectinload(StudentEnrollment.student).selectinload(Student.person),
            selectinload(StudentEnrollment.cohort),
            selectinload(StudentEnrollment.academic_year),
        )
        .where(StudentEnrollment.school_id == school_id)
    )
    if student_id is not None:
        stmt = stmt.where(StudentEnrollment.student_id == student_id)
    if academic_year_id is not None:
        stmt = stmt.where(StudentEnrollment.academic_year_id == academic_year_id)
    if cohort_id is not None:
        stmt = stmt.where(StudentEnrollment.cohort_id == cohort_id)
    if status is not None:
        stmt = stmt.where(StudentEnrollment.status == status.value)
    return await paginate_cursor(session, stmt, params, model=StudentEnrollment)


async def get_active_for_student_year(
    session: AsyncSession,
    student_id: str,
    academic_year_id: str,
) -> StudentEnrollment | None:
    stmt = select(StudentEnrollment).where(
        StudentEnrollment.student_id == student_id,
        StudentEnrollment.academic_year_id == academic_year_id,
        StudentEnrollment.status == EnrollmentStatus.ACTIVE.value,
    )
    return (await session.scalars(stmt)).first()


async def get_active_roll_in_cohort(
    session: AsyncSession,
    cohort_id: str,
    roll_number: str,
) -> StudentEnrollment | None:
    stmt = select(StudentEnrollment).where(
        StudentEnrollment.cohort_id == cohort_id,
        StudentEnrollment.roll_number == roll_number,
        StudentEnrollment.status == EnrollmentStatus.ACTIVE.value,
    )
    return (await session.scalars(stmt)).first()
