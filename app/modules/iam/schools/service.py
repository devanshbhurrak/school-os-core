"""School business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.iam.models import School
from app.modules.iam.schools import repository
from app.modules.iam.schools.schemas import SchoolCreate, SchoolUpdate
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = [
    "code", "name", "short_name", "status", "board", "affiliation_number",
    "contact_email", "contact_phone", "timezone", "locale",
]


async def create(
    session: AsyncSession,
    ctx: RequestContext,
    data: SchoolCreate,
) -> School:
    if ctx.organization_id is None:
        raise InvalidRequestError("No organization context is set for this request.")

    if await repository.get_by_code(session, ctx.organization_id, data.code):
        raise ConflictError(
            f"A school with code {data.code!r} already exists.",
            code="SCHOOL_CODE_TAKEN",
            details={"code": data.code},
        )

    instance = School(
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        code=data.code,
        name=data.name,
        short_name=data.short_name,
        board=data.board,
        affiliation_number=data.affiliation_number,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="SCHOOL_CREATED",
        entity_type="school",
        entity_id=instance.id,
        summary=f"School {instance.code!r} created",
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    school: School,
    data: SchoolUpdate,
) -> School:
    if school.version != data.version:
        raise StaleResourceError()

    before = snapshot(school, _SNAPSHOT_FIELDS)
    for field, value in data.model_dump(exclude={"version"}, exclude_none=True).items():
        setattr(school, field, value)
    school.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="SCHOOL_UPDATED",
        entity_type="school",
        entity_id=school.id,
        summary=f"School {school.code!r} updated",
        before=before,
        after=snapshot(school, _SNAPSHOT_FIELDS),
    )
    return school


async def delete(
    session: AsyncSession,
    ctx: RequestContext,
    school: School,
    version: int,
) -> None:
    if school.version != version:
        raise StaleResourceError()

    before = snapshot(school, _SNAPSHOT_FIELDS)
    school.deleted_at = datetime.now(UTC)
    school.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="SCHOOL_DELETED",
        entity_type="school",
        entity_id=school.id,
        summary=f"School {school.code!r} deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, school_id: str) -> School:
    if ctx.organization_id is None:
        raise NotFoundError("The school was not found.", code="SCHOOL_NOT_FOUND")
    school = await repository.get_by_id(session, ctx.organization_id, school_id)
    if school is None:
        raise NotFoundError("The school was not found.", code="SCHOOL_NOT_FOUND")
    return school
