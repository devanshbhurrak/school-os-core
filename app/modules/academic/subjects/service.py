"""Subject business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.academic.models import Subject
from app.modules.academic.subjects import repository
from app.modules.academic.subjects.schemas import SubjectCreate, SubjectUpdate
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["code", "name", "description", "subject_type", "status"]


async def create(session: AsyncSession, ctx: RequestContext, data: SubjectCreate) -> Subject:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    if await repository.get_by_code(session, ctx.school_id, data.code):
        raise ConflictError(
            f"A subject with code {data.code!r} already exists.",
            code="SUBJECT_CODE_TAKEN",
            details={"code": data.code},
        )

    instance = Subject(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="SUBJECT_CREATED",
        entity_type="subject",
        entity_id=instance.id,
        summary=f"Subject {instance.code!r} created",
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    subject: Subject,
    data: SubjectUpdate,
) -> Subject:
    if subject.version != data.version:
        raise StaleResourceError()

    before = snapshot(subject, _SNAPSHOT_FIELDS)
    for field, value in data.model_dump(exclude={"version"}, exclude_none=True).items():
        setattr(subject, field, value)
    subject.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="SUBJECT_UPDATED",
        entity_type="subject",
        entity_id=subject.id,
        summary=f"Subject {subject.code!r} updated",
        before=before,
        after=snapshot(subject, _SNAPSHOT_FIELDS),
    )
    return subject


async def delete(session: AsyncSession, ctx: RequestContext, subject: Subject, version: int) -> None:
    if subject.version != version:
        raise StaleResourceError()

    before = snapshot(subject, _SNAPSHOT_FIELDS)
    subject.deleted_at = datetime.now(UTC)
    subject.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="SUBJECT_DELETED",
        entity_type="subject",
        entity_id=subject.id,
        summary=f"Subject {subject.code!r} deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, subject_id: str) -> Subject:
    if ctx.school_id is None:
        raise NotFoundError("The subject was not found.", code="SUBJECT_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, subject_id)
    if obj is None:
        raise NotFoundError("The subject was not found.", code="SUBJECT_NOT_FOUND")
    return obj
