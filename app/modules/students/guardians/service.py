"""Guardian business logic."""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError
from app.modules.people.models import Person
from app.modules.students.guardians import repository
from app.modules.students.guardians.schemas import GuardianCreate, GuardianUpdate
from app.modules.students.models import Student, StudentGuardian
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["student_id", "guardian_person_id", "relationship", "is_primary",
                    "is_emergency_contact", "can_pickup"]


def _guardian_snapshot(guardian: StudentGuardian) -> dict:
    return snapshot(guardian, _SNAPSHOT_FIELDS)


async def add_guardian(
    session: AsyncSession, ctx: RequestContext, payload: GuardianCreate
) -> StudentGuardian:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Validate student exists in school
    student = await session.scalar(
        select(Student).where(
            Student.id == payload.student_id,
            Student.school_id == ctx.school_id,
            Student.deleted_at.is_(None),
        )
    )
    if student is None:
        raise NotFoundError("The specified student was not found.", code="STUDENT_NOT_FOUND")

    # Validate guardian person exists in same organization
    person = await session.scalar(
        select(Person).where(
            Person.id == payload.guardian_person_id,
            Person.organization_id == ctx.organization_id,
            Person.deleted_at.is_(None),
        )
    )
    if person is None:
        raise NotFoundError(
            "The specified person does not exist in this organization.",
            code="PERSON_NOT_FOUND",
        )

    # Check uniqueness
    existing = await repository.get_by_student_and_person(
        session, payload.student_id, payload.guardian_person_id, ctx.school_id
    )
    if existing is not None:
        raise ConflictError(
            "This person is already linked as a guardian for this student.",
            code="GUARDIAN_ALREADY_LINKED",
            details={"student_id": payload.student_id, "guardian_person_id": payload.guardian_person_id},
        )

    instance = StudentGuardian(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        student_id=payload.student_id,
        guardian_person_id=payload.guardian_person_id,
        relationship=payload.relationship.value,
        is_primary=payload.is_primary,
        is_emergency_contact=payload.is_emergency_contact,
        can_pickup=payload.can_pickup,
    )
    session.add(instance)
    await session.flush()

    # If is_primary, unset on all other guardians for this student
    if payload.is_primary:
        await session.execute(
            update(StudentGuardian)
            .where(
                StudentGuardian.student_id == payload.student_id,
                StudentGuardian.school_id == ctx.school_id,
                StudentGuardian.id != instance.id,
            )
            .values(is_primary=False)
        )

    instance.guardian_person = person  # type: ignore[assignment]

    await audit(
        session, ctx,
        action="STUDENT_GUARDIAN_CREATED",
        entity_type="student_guardian",
        entity_id=instance.id,
        summary=f"Guardian linked to student {payload.student_id!r}",
        after=_guardian_snapshot(instance),
    )
    return instance


async def update_guardian(
    session: AsyncSession,
    ctx: RequestContext,
    guardian_id: str,
    payload: GuardianUpdate,
) -> StudentGuardian:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    guardian = await repository.get_by_id(session, guardian_id, ctx.school_id)
    if guardian is None:
        raise NotFoundError("The guardian link was not found.", code="GUARDIAN_NOT_FOUND")

    before = _guardian_snapshot(guardian)
    changes = payload.model_dump(exclude_none=True)

    # If is_primary being set to True, unset on others first
    if changes.get("is_primary") is True:
        await session.execute(
            update(StudentGuardian)
            .where(
                StudentGuardian.student_id == guardian.student_id,
                StudentGuardian.school_id == ctx.school_id,
                StudentGuardian.id != guardian.id,
            )
            .values(is_primary=False)
        )

    for field, value in changes.items():
        if field == "relationship":
            setattr(guardian, field, value.value if hasattr(value, "value") else value)
        else:
            setattr(guardian, field, value)
    guardian.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="STUDENT_GUARDIAN_UPDATED",
        entity_type="student_guardian",
        entity_id=guardian.id,
        summary=f"Guardian link {guardian.id!r} updated",
        before=before,
        after=_guardian_snapshot(guardian),
    )
    return guardian


async def remove_guardian(
    session: AsyncSession, ctx: RequestContext, guardian_id: str
) -> None:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    guardian = await repository.get_by_id(session, guardian_id, ctx.school_id)
    if guardian is None:
        raise NotFoundError("The guardian link was not found.", code="GUARDIAN_NOT_FOUND")

    before = _guardian_snapshot(guardian)
    await session.delete(guardian)
    await session.flush()

    await audit(
        session, ctx,
        action="STUDENT_GUARDIAN_DELETED",
        entity_type="student_guardian",
        entity_id=guardian_id,
        summary=f"Guardian link {guardian_id!r} removed",
        before=before,
    )
