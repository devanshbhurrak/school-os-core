"""Teacher data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.academic.models import AcademicYear, Cohort, Subject
from app.modules.people.models import Person
from app.modules.teachers.enums import AssignmentRole, AssignmentStatus
from app.modules.teachers.models import Teacher, TeacherAssignment


async def get_by_id(
    session: AsyncSession, school_id: str, teacher_id: str
) -> Teacher | None:
    stmt = (
        select(Teacher)
        .options(selectinload(Teacher.person))
        .where(
            Teacher.id == teacher_id,
            Teacher.school_id == school_id,
            Teacher.deleted_at.is_(None),
        )
    )
    return (await session.scalars(stmt)).first()


async def get_by_person_id(
    session: AsyncSession, school_id: str, person_id: str
) -> Teacher | None:
    stmt = select(Teacher).where(
        Teacher.school_id == school_id,
        Teacher.person_id == person_id,
        Teacher.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_teachers(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    search: str | None = None,
    status: str | None = None,
) -> CursorPage[Teacher]:
    stmt = (
        select(Teacher)
        .join(Person, Teacher.person_id == Person.id)
        .where(
            Teacher.school_id == school_id,
            Teacher.deleted_at.is_(None),
        )
    )
    if search:
        pattern = f"%{search.strip().lower()}%"
        full_name = func.lower(
            func.concat_ws(" ", Person.first_name, Person.last_name)
        )
        stmt = stmt.where(
            (full_name.like(pattern))
            | (Person.primary_email.is_not(None) & func.lower(Person.primary_email).like(pattern))
        )
    if status:
        stmt = stmt.where(Teacher.status == status)
    return await paginate_cursor(session, stmt, params, model=Teacher)


async def get_assignment_by_id(
    session: AsyncSession, school_id: str, assignment_id: str
) -> TeacherAssignment | None:
    stmt = select(TeacherAssignment).where(
        TeacherAssignment.id == assignment_id,
        TeacherAssignment.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()


async def list_assignments(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    teacher_id: str | None = None,
    cohort_id: str | None = None,
    academic_year_id: str | None = None,
    status: str | None = None,
) -> CursorPage[TeacherAssignment]:
    stmt = select(TeacherAssignment).where(
        TeacherAssignment.school_id == school_id,
    )
    if teacher_id:
        stmt = stmt.where(TeacherAssignment.teacher_id == teacher_id)
    if cohort_id:
        stmt = stmt.where(TeacherAssignment.cohort_id == cohort_id)
    if academic_year_id:
        stmt = stmt.where(TeacherAssignment.academic_year_id == academic_year_id)
    if status:
        stmt = stmt.where(TeacherAssignment.status == status)
    return await paginate_cursor(session, stmt, params, model=TeacherAssignment)


async def check_assignment_conflict(
    session: AsyncSession,
    school_id: str,
    cohort_id: str,
    subject_id: str | None,
    academic_year_id: str,
    role: AssignmentRole,
    *,
    exclude_id: str | None = None,
) -> bool:
    """Return True if a conflicting ACTIVE assignment exists."""
    if role == AssignmentRole.SUBJECT_TEACHER:
        stmt = select(TeacherAssignment.id).where(
            TeacherAssignment.school_id == school_id,
            TeacherAssignment.cohort_id == cohort_id,
            TeacherAssignment.subject_id == subject_id,
            TeacherAssignment.academic_year_id == academic_year_id,
            TeacherAssignment.role == AssignmentRole.SUBJECT_TEACHER,
            TeacherAssignment.status == AssignmentStatus.ACTIVE,
        )
    elif role == AssignmentRole.CLASS_TEACHER:
        stmt = select(TeacherAssignment.id).where(
            TeacherAssignment.school_id == school_id,
            TeacherAssignment.cohort_id == cohort_id,
            TeacherAssignment.academic_year_id == academic_year_id,
            TeacherAssignment.role == AssignmentRole.CLASS_TEACHER,
            TeacherAssignment.status == AssignmentStatus.ACTIVE,
        )
    else:
        return False

    if exclude_id:
        stmt = stmt.where(TeacherAssignment.id != exclude_id)

    result = (await session.scalars(stmt)).first()
    return result is not None


async def load_assignment_joined(
    session: AsyncSession, assignment: TeacherAssignment
) -> dict:
    """Load joined display fields for an assignment."""
    teacher_stmt = (
        select(Teacher)
        .options(selectinload(Teacher.person))
        .where(Teacher.id == assignment.teacher_id)
    )
    teacher = (await session.scalars(teacher_stmt)).first()

    cohort_stmt = select(Cohort).where(Cohort.id == assignment.cohort_id)
    cohort = (await session.scalars(cohort_stmt)).first()

    subject = None
    if assignment.subject_id:
        subject_stmt = select(Subject).where(Subject.id == assignment.subject_id)
        subject = (await session.scalars(subject_stmt)).first()

    year_stmt = select(AcademicYear).where(AcademicYear.id == assignment.academic_year_id)
    year = (await session.scalars(year_stmt)).first()

    return {
        "teacher": teacher,
        "cohort": cohort,
        "subject": subject,
        "year": year,
    }
