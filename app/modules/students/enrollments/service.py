"""Enrollment business logic."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.academic.models import AcademicYear, Cohort
from app.modules.students import repository as student_repo
from app.modules.students.enrollments import repository
from app.modules.students.enrollments.schemas import (
    EnrollmentCreate,
    EnrollmentTransfer,
    EnrollmentUpdate,
)
from app.modules.students.enums import EnrollmentStatus, EnrollmentType
from app.modules.students.models import StudentEnrollment
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["student_id", "academic_year_id", "cohort_id", "roll_number", "status", "enrollment_type"]


def _enrollment_snapshot(enrollment: StudentEnrollment) -> dict:
    s = snapshot(enrollment, _SNAPSHOT_FIELDS)
    s["start_date"] = str(enrollment.start_date) if enrollment.start_date else None
    s["end_date"] = str(enrollment.end_date) if enrollment.end_date else None
    return s


async def create(
    session: AsyncSession, ctx: RequestContext, data: EnrollmentCreate
) -> StudentEnrollment:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Validate student exists in same school
    student = await student_repo.get_by_id(session, ctx.school_id, data.student_id)
    if student is None:
        raise NotFoundError("The specified student does not exist in this school.", code="STUDENT_NOT_FOUND")

    # Validate cohort exists in same school
    cohort = await session.scalar(
        select(Cohort).where(
            Cohort.id == data.cohort_id,
            Cohort.school_id == ctx.school_id,
            Cohort.deleted_at.is_(None),
        )
    )
    if cohort is None:
        raise NotFoundError("The specified cohort does not exist in this school.", code="COHORT_NOT_FOUND")

    # Validate academic year exists in same school
    academic_year = await session.scalar(
        select(AcademicYear).where(
            AcademicYear.id == data.academic_year_id,
            AcademicYear.school_id == ctx.school_id,
            AcademicYear.deleted_at.is_(None),
        )
    )
    if academic_year is None:
        raise NotFoundError(
            "The specified academic year does not exist in this school.",
            code="ACADEMIC_YEAR_NOT_FOUND",
        )

    # Check no ACTIVE enrollment exists for this student + year
    existing = await repository.get_active_for_student_year(
        session, data.student_id, data.academic_year_id
    )
    if existing is not None:
        raise ConflictError(
            "This student already has an active enrollment for the specified academic year.",
            code="ALREADY_ENROLLED",
            details={"student_id": data.student_id, "academic_year_id": data.academic_year_id},
        )

    # Check roll_number unique in cohort if provided
    if data.roll_number:
        duplicate = await repository.get_active_roll_in_cohort(
            session, data.cohort_id, data.roll_number
        )
        if duplicate is not None:
            raise ConflictError(
                f"Roll number {data.roll_number!r} is already taken in this cohort.",
                code="ROLL_NUMBER_TAKEN",
                details={"roll_number": data.roll_number, "cohort_id": data.cohort_id},
            )

    instance = StudentEnrollment(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        student_id=data.student_id,
        academic_year_id=data.academic_year_id,
        academic_class_id=data.academic_class_id,
        cohort_id=data.cohort_id,
        roll_number=data.roll_number,
        start_date=data.start_date,
        enrollment_type=data.enrollment_type.value,
        status=EnrollmentStatus.ACTIVE.value,
    )
    session.add(instance)
    await session.flush()

    # Attach relations for snapshot/response
    instance.student = student  # type: ignore[assignment]
    instance.cohort = cohort  # type: ignore[assignment]
    instance.academic_year = academic_year  # type: ignore[assignment]

    await audit(
        session, ctx,
        action="ENROLLMENT_CREATED",
        entity_type="student_enrollment",
        entity_id=instance.id,
        summary=f"Enrollment created for student {data.student_id!r}",
        after=_enrollment_snapshot(instance),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    enrollment_id: str,
    data: EnrollmentUpdate,
) -> StudentEnrollment:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    enrollment = await repository.get_by_id(session, enrollment_id, ctx.school_id)
    if enrollment is None:
        raise NotFoundError("The enrollment was not found.", code="ENROLLMENT_NOT_FOUND")

    if enrollment.version != data.version:
        raise StaleResourceError()

    before = _enrollment_snapshot(enrollment)
    payload = data.model_dump(exclude={"version"}, exclude_unset=True)
    for field, value in payload.items():
        setattr(enrollment, field, value)
    enrollment.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ENROLLMENT_UPDATED",
        entity_type="student_enrollment",
        entity_id=enrollment.id,
        summary=f"Enrollment {enrollment.id!r} updated",
        before=before,
        after=_enrollment_snapshot(enrollment),
    )
    return enrollment


async def transfer(
    session: AsyncSession,
    ctx: RequestContext,
    enrollment_id: str,
    data: EnrollmentTransfer,
) -> StudentEnrollment:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    old = await repository.get_by_id(session, enrollment_id, ctx.school_id)
    if old is None:
        raise NotFoundError("The enrollment was not found.", code="ENROLLMENT_NOT_FOUND")

    if old.status != EnrollmentStatus.ACTIVE.value:
        raise ConflictError(
            "Only ACTIVE enrollments can be transferred.",
            code="ENROLLMENT_NOT_ACTIVE",
        )

    # Validate new cohort
    new_cohort = await session.scalar(
        select(Cohort).where(
            Cohort.id == data.new_cohort_id,
            Cohort.school_id == ctx.school_id,
            Cohort.deleted_at.is_(None),
        )
    )
    if new_cohort is None:
        raise NotFoundError("The specified cohort does not exist in this school.", code="COHORT_NOT_FOUND")

    before = _enrollment_snapshot(old)

    # End the old enrollment
    old.end_date = data.effective_date
    old.status = EnrollmentStatus.TRANSFERRED.value
    old.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ENROLLMENT_UPDATED",
        entity_type="student_enrollment",
        entity_id=old.id,
        summary=f"Enrollment {old.id!r} ended by transfer",
        before=before,
        after=_enrollment_snapshot(old),
    )

    # Create the new enrollment
    new_enrollment = StudentEnrollment(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        student_id=old.student_id,
        academic_year_id=old.academic_year_id,
        academic_class_id=data.new_academic_class_id,
        cohort_id=data.new_cohort_id,
        roll_number=None,
        start_date=data.effective_date,
        enrollment_type=EnrollmentType.TRANSFER_IN.value,
        status=EnrollmentStatus.ACTIVE.value,
    )
    session.add(new_enrollment)
    await session.flush()

    new_enrollment.cohort = new_cohort  # type: ignore[assignment]
    new_enrollment.academic_year = old.academic_year  # type: ignore[assignment]
    new_enrollment.student = old.student  # type: ignore[assignment]

    await audit(
        session, ctx,
        action="ENROLLMENT_CREATED",
        entity_type="student_enrollment",
        entity_id=new_enrollment.id,
        summary=f"Enrollment created via transfer for student {old.student_id!r}",
        after=_enrollment_snapshot(new_enrollment),
    )
    return new_enrollment


async def delete(
    session: AsyncSession,
    ctx: RequestContext,
    enrollment_id: str,
    version: int,
) -> None:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    enrollment = await repository.get_by_id(session, enrollment_id, ctx.school_id)
    if enrollment is None:
        raise NotFoundError("The enrollment was not found.", code="ENROLLMENT_NOT_FOUND")

    if enrollment.version != version:
        raise StaleResourceError()

    if enrollment.status != EnrollmentStatus.ACTIVE.value:
        raise ConflictError(
            "Only ACTIVE enrollments can be deleted.",
            code="ENROLLMENT_NOT_ACTIVE",
        )

    before = _enrollment_snapshot(enrollment)
    await session.delete(enrollment)
    await session.flush()

    await audit(
        session, ctx,
        action="ENROLLMENT_DELETED",
        entity_type="student_enrollment",
        entity_id=enrollment_id,
        summary=f"Enrollment {enrollment_id!r} deleted",
        before=before,
    )


async def get_owned(
    session: AsyncSession, ctx: RequestContext, enrollment_id: str
) -> StudentEnrollment:
    if ctx.school_id is None:
        raise NotFoundError("The enrollment was not found.", code="ENROLLMENT_NOT_FOUND")
    obj = await repository.get_by_id(session, enrollment_id, ctx.school_id)
    if obj is None:
        raise NotFoundError("The enrollment was not found.", code="ENROLLMENT_NOT_FOUND")
    return obj
