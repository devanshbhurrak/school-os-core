"""AcademicClass business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.academic.academic_classes import repository
from app.modules.academic.academic_classes.schemas import AcademicClassCreate, AcademicClassUpdate
from app.modules.academic.models import AcademicClass
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["code", "name", "description", "sort_order", "status"]


async def create(session: AsyncSession, ctx: RequestContext, data: AcademicClassCreate) -> AcademicClass:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    if await repository.get_by_code(session, ctx.school_id, data.code):
        raise ConflictError(
            f"An academic class with code {data.code!r} already exists.",
            code="ACADEMIC_CLASS_CODE_TAKEN",
            details={"code": data.code},
        )

    instance = AcademicClass(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="ACADEMIC_CLASS_CREATED",
        entity_type="academic_class",
        entity_id=instance.id,
        summary=f"Academic class {instance.code!r} created",
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    academic_class: AcademicClass,
    data: AcademicClassUpdate,
) -> AcademicClass:
    if academic_class.version != data.version:
        raise StaleResourceError()

    before = snapshot(academic_class, _SNAPSHOT_FIELDS)
    for field, value in data.model_dump(exclude={"version"}, exclude_none=True).items():
        setattr(academic_class, field, value)
    academic_class.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ACADEMIC_CLASS_UPDATED",
        entity_type="academic_class",
        entity_id=academic_class.id,
        summary=f"Academic class {academic_class.code!r} updated",
        before=before,
        after=snapshot(academic_class, _SNAPSHOT_FIELDS),
    )
    return academic_class


async def delete(session: AsyncSession, ctx: RequestContext, academic_class: AcademicClass, version: int) -> None:
    if academic_class.version != version:
        raise StaleResourceError()

    before = snapshot(academic_class, _SNAPSHOT_FIELDS)
    academic_class.deleted_at = datetime.now(UTC)
    academic_class.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ACADEMIC_CLASS_DELETED",
        entity_type="academic_class",
        entity_id=academic_class.id,
        summary=f"Academic class {academic_class.code!r} deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, academic_class_id: str) -> AcademicClass:
    if ctx.school_id is None:
        raise NotFoundError("The academic class was not found.", code="ACADEMIC_CLASS_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, academic_class_id)
    if obj is None:
        raise NotFoundError("The academic class was not found.", code="ACADEMIC_CLASS_NOT_FOUND")
    return obj
