"""Teacher business logic."""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.academic.models import AcademicYear, Cohort
from app.modules.people.models import Person
from app.modules.teachers import repository
from app.modules.teachers.enums import AssignmentStatus
from app.modules.teachers.models import Teacher, TeacherAssignment
from app.modules.teachers.schemas import AssignmentCreate, AssignmentUpdate, TeacherCreate, TeacherUpdate
from app.modules.platform_.audit.service import audit, snapshot

_TEACHER_SNAPSHOT_FIELDS = ["employee_number", "designation", "status"]
_ASSIGNMENT_SNAPSHOT_FIELDS = ["role", "status"]


def _teacher_snapshot(teacher: Teacher) -> dict:
    s = snapshot(teacher, _TEACHER_SNAPSHOT_FIELDS)
    s["joining_date"] = str(teacher.joining_date) if teacher.joining_date else None
    s["leaving_date"] = str(teacher.leaving_date) if teacher.leaving_date else None
    return s


def _assignment_snapshot(assignment: TeacherAssignment) -> dict:
    s = snapshot(assignment, _ASSIGNMENT_SNAPSHOT_FIELDS)
    s["start_date"] = str(assignment.start_date) if assignment.start_date else None
    s["end_date"] = str(assignment.end_date) if assignment.end_date else None
    return s


async def _get_person(session: AsyncSession, organization_id: str, person_id: str) -> Person:
    stmt = select(Person).where(
        Person.id == person_id,
        Person.organization_id == organization_id,
        Person.deleted_at.is_(None),
    )
    person = (await session.scalars(stmt)).first()
    if person is None:
        raise NotFoundError("The person was not found.", code="PERSON_NOT_FOUND")
    return person


async def create(
    session: AsyncSession, ctx: RequestContext, data: TeacherCreate
) -> Teacher:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Validate person belongs to same org
    person = await _get_person(session, ctx.organization_id, data.person_id)

    # Check person not already a teacher at this school
    existing = await repository.get_by_person_id(session, ctx.school_id, data.person_id)
    if existing is not None:
        raise ConflictError(
            "This person is already a teacher at this school.",
            code="TEACHER_PERSON_TAKEN",
            details={"person_id": data.person_id},
        )

    # Validate employee_number uniqueness if provided
    if data.employee_number:
        emp_stmt = select(Teacher).where(
            Teacher.school_id == ctx.school_id,
            Teacher.employee_number == data.employee_number,
            Teacher.deleted_at.is_(None),
        )
        if (await session.scalars(emp_stmt)).first() is not None:
            raise ConflictError(
                f"Employee number {data.employee_number!r} is already in use.",
                code="EMPLOYEE_NUMBER_TAKEN",
                details={"employee_number": data.employee_number},
            )

    instance = Teacher(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()
    # Reload with person eagerly loaded so the router can access it
    reloaded = await repository.get_by_id(session, ctx.school_id, instance.id)
    if reloaded is not None:
        instance = reloaded

    await audit(
        session, ctx,
        action="TEACHER_CREATED",
        entity_type="teacher",
        entity_id=instance.id,
        summary=f"Teacher {person.first_name} {person.last_name or ''} created".strip(),
        after=_teacher_snapshot(instance),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    teacher: Teacher,
    data: TeacherUpdate,
) -> Teacher:
    if teacher.version != data.version:
        raise StaleResourceError()

    # Check employee_number uniqueness if changing
    if data.employee_number is not None and data.employee_number != teacher.employee_number:
        emp_stmt = select(Teacher).where(
            Teacher.school_id == teacher.school_id,
            Teacher.employee_number == data.employee_number,
            Teacher.deleted_at.is_(None),
            Teacher.id != teacher.id,
        )
        if (await session.scalars(emp_stmt)).first() is not None:
            raise ConflictError(
                f"Employee number {data.employee_number!r} is already in use.",
                code="EMPLOYEE_NUMBER_TAKEN",
                details={"employee_number": data.employee_number},
            )

    before = _teacher_snapshot(teacher)
    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    for field, value in payload.items():
        setattr(teacher, field, value)
    teacher.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TEACHER_UPDATED",
        entity_type="teacher",
        entity_id=teacher.id,
        summary="Teacher updated",
        before=before,
        after=_teacher_snapshot(teacher),
    )
    return teacher


async def delete(
    session: AsyncSession, ctx: RequestContext, teacher: Teacher, version: int
) -> None:
    if teacher.version != version:
        raise StaleResourceError()

    before = _teacher_snapshot(teacher)
    teacher.deleted_at = datetime.now(UTC)
    teacher.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TEACHER_DELETED",
        entity_type="teacher",
        entity_id=teacher.id,
        summary="Teacher deleted",
        before=before,
    )


async def get_owned(
    session: AsyncSession, ctx: RequestContext, teacher_id: str
) -> Teacher:
    if ctx.school_id is None:
        raise NotFoundError("The teacher was not found.", code="TEACHER_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, teacher_id)
    if obj is None:
        raise NotFoundError("The teacher was not found.", code="TEACHER_NOT_FOUND")
    return obj


async def create_assignment(
    session: AsyncSession, ctx: RequestContext, data: AssignmentCreate
) -> TeacherAssignment:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Validate teacher belongs to this school
    teacher = await repository.get_by_id(session, ctx.school_id, data.teacher_id)
    if teacher is None:
        raise NotFoundError("The teacher was not found.", code="TEACHER_NOT_FOUND")

    # Validate cohort belongs to this school
    cohort_stmt = select(Cohort).where(
        Cohort.id == data.cohort_id,
        Cohort.school_id == ctx.school_id,
        Cohort.deleted_at.is_(None),
    )
    cohort = (await session.scalars(cohort_stmt)).first()
    if cohort is None:
        raise NotFoundError("The cohort was not found.", code="COHORT_NOT_FOUND")

    # Validate academic year belongs to this school
    year_stmt = select(AcademicYear).where(
        AcademicYear.id == data.academic_year_id,
        AcademicYear.school_id == ctx.school_id,
        AcademicYear.deleted_at.is_(None),
    )
    year = (await session.scalars(year_stmt)).first()
    if year is None:
        raise NotFoundError("The academic year was not found.", code="ACADEMIC_YEAR_NOT_FOUND")

    # Check for assignment conflicts
    has_conflict = await repository.check_assignment_conflict(
        session,
        ctx.school_id,
        data.cohort_id,
        data.subject_id,
        data.academic_year_id,
        data.role,
    )
    if has_conflict:
        raise ConflictError(
            "An active assignment already exists for this cohort, subject, and year.",
            code="ASSIGNMENT_CONFLICT",
        )

    instance = TeacherAssignment(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="TEACHER_ASSIGNED",
        entity_type="teacher_assignment",
        entity_id=instance.id,
        summary=f"Teacher assigned to cohort {cohort.name}",
        after=_assignment_snapshot(instance),
    )
    return instance


async def update_assignment(
    session: AsyncSession,
    ctx: RequestContext,
    assignment: TeacherAssignment,
    data: AssignmentUpdate,
) -> TeacherAssignment:
    if assignment.version != data.version:
        raise StaleResourceError()

    before = _assignment_snapshot(assignment)
    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    for field, value in payload.items():
        setattr(assignment, field, value)
    assignment.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TEACHER_ASSIGNMENT_UPDATED",
        entity_type="teacher_assignment",
        entity_id=assignment.id,
        summary="Teacher assignment updated",
        before=before,
        after=_assignment_snapshot(assignment),
    )
    return assignment


async def end_assignment(
    session: AsyncSession,
    ctx: RequestContext,
    assignment: TeacherAssignment,
    version: int,
) -> TeacherAssignment:
    """Soft-delete assignment by setting status=ENDED and end_date=today."""
    if assignment.version != version:
        raise StaleResourceError()

    before = _assignment_snapshot(assignment)
    assignment.status = AssignmentStatus.ENDED
    assignment.end_date = date.today()
    assignment.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="TEACHER_ASSIGNMENT_ENDED",
        entity_type="teacher_assignment",
        entity_id=assignment.id,
        summary="Teacher assignment ended",
        before=before,
        after=_assignment_snapshot(assignment),
    )
    return assignment


async def get_assignment_owned(
    session: AsyncSession, ctx: RequestContext, assignment_id: str
) -> TeacherAssignment:
    if ctx.school_id is None:
        raise NotFoundError("The assignment was not found.", code="ASSIGNMENT_NOT_FOUND")
    obj = await repository.get_assignment_by_id(session, ctx.school_id, assignment_id)
    if obj is None:
        raise NotFoundError("The assignment was not found.", code="ASSIGNMENT_NOT_FOUND")
    return obj
