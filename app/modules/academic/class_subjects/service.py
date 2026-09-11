"""ClassSubject business logic."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError
from app.modules.academic.academic_classes import repository as classes_repository
from app.modules.academic.academic_years import repository as years_repository
from app.modules.academic.class_subjects import repository
from app.modules.academic.class_subjects.schemas import ClassSubjectCreate
from app.modules.academic.models import ClassSubject
from app.modules.academic.subjects import repository as subjects_repository
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["academic_class_id", "subject_id", "effective_from_year_id", "effective_to_year_id"]


async def create(session: AsyncSession, ctx: RequestContext, data: ClassSubjectCreate) -> ClassSubject:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    if not await classes_repository.get_by_id(session, ctx.school_id, data.academic_class_id):
        raise NotFoundError("The academic class was not found.", code="ACADEMIC_CLASS_NOT_FOUND")

    if not await subjects_repository.get_by_id(session, ctx.school_id, data.subject_id):
        raise NotFoundError("The subject was not found.", code="SUBJECT_NOT_FOUND")

    if not await years_repository.get_by_id(session, ctx.school_id, data.effective_from_year_id):
        raise NotFoundError("The academic year was not found.", code="ACADEMIC_YEAR_NOT_FOUND")

    if await repository.get_existing(session, ctx.school_id, data.academic_class_id, data.subject_id):
        raise ConflictError(
            "This subject is already assigned to the academic class.",
            code="CLASS_SUBJECT_ALREADY_EXISTS",
        )

    instance = ClassSubject(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="CLASS_SUBJECT_CREATED",
        entity_type="class_subject",
        entity_id=instance.id,
        summary="Class subject link created",
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def delete(session: AsyncSession, ctx: RequestContext, class_subject: ClassSubject) -> None:
    before = snapshot(class_subject, _SNAPSHOT_FIELDS)
    await session.delete(class_subject)
    await session.flush()

    await audit(
        session, ctx,
        action="CLASS_SUBJECT_DELETED",
        entity_type="class_subject",
        entity_id=class_subject.id,
        summary="Class subject link deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, class_subject_id: str) -> ClassSubject:
    if ctx.school_id is None:
        raise NotFoundError("The class subject was not found.", code="CLASS_SUBJECT_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, class_subject_id)
    if obj is None:
        raise NotFoundError("The class subject was not found.", code="CLASS_SUBJECT_NOT_FOUND")
    return obj
