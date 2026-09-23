"""Student business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.people.models import Person
from app.modules.students import repository
from app.modules.students.models import Student
from app.modules.students.schemas import StudentCreate, StudentUpdate
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["admission_number", "status", "admission_date"]


def _student_snapshot(student: Student) -> dict:
    s = snapshot(student, _SNAPSHOT_FIELDS)
    s["admission_date"] = str(student.admission_date) if student.admission_date else None
    return s


async def create(session: AsyncSession, ctx: RequestContext, data: StudentCreate) -> Student:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Validate person exists in this organization
    person = await session.scalar(
        select(Person).where(
            Person.id == data.person_id,
            Person.organization_id == ctx.organization_id,
            Person.deleted_at.is_(None),
        )
    )
    if person is None:
        raise NotFoundError(
            "The specified person does not exist in this organization.",
            code="PERSON_NOT_FOUND",
        )

    # Validate admission_number unique within school
    if await repository.get_by_admission_number(session, ctx.school_id, data.admission_number):
        raise ConflictError(
            f"A student with admission number {data.admission_number!r} already exists.",
            code="ADMISSION_NUMBER_TAKEN",
            details={"admission_number": data.admission_number},
        )

    # Validate person not already a student at this school
    if await repository.get_by_person_id(session, ctx.school_id, data.person_id):
        raise ConflictError(
            "This person is already enrolled as a student at this school.",
            code="PERSON_ALREADY_ENROLLED",
            details={"person_id": data.person_id},
        )

    instance = Student(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    # Load person for snapshot/response
    instance.person = person  # type: ignore[assignment]

    await audit(
        session, ctx,
        action="STUDENT_CREATED",
        entity_type="student",
        entity_id=instance.id,
        summary=f"Student {instance.admission_number!r} created",
        after=_student_snapshot(instance),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    student: Student,
    data: StudentUpdate,
) -> Student:
    if student.version != data.version:
        raise StaleResourceError()

    before = _student_snapshot(student)
    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    for field, value in payload.items():
        setattr(student, field, value)
    student.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="STUDENT_UPDATED",
        entity_type="student",
        entity_id=student.id,
        summary=f"Student {student.admission_number!r} updated",
        before=before,
        after=_student_snapshot(student),
    )
    return student


async def delete(session: AsyncSession, ctx: RequestContext, student: Student, version: int) -> None:
    if student.version != version:
        raise StaleResourceError()

    before = _student_snapshot(student)
    student.deleted_at = datetime.now(UTC)
    student.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="STUDENT_DELETED",
        entity_type="student",
        entity_id=student.id,
        summary=f"Student {student.admission_number!r} deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, student_id: str) -> Student:
    if ctx.school_id is None:
        raise NotFoundError("The student was not found.", code="STUDENT_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, student_id)
    if obj is None:
        raise NotFoundError("The student was not found.", code="STUDENT_NOT_FOUND")
    return obj
