"""AcademicYear business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.academic.academic_years import repository
from app.modules.academic.academic_years.schemas import AcademicYearCreate, AcademicYearUpdate
from app.modules.academic.models import AcademicYear
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["code", "name", "is_current", "status"]


def _year_snapshot(year: AcademicYear) -> dict:
    s = snapshot(year, _SNAPSHOT_FIELDS)
    s["start_date"] = str(year.start_date) if year.start_date else None
    s["end_date"] = str(year.end_date) if year.end_date else None
    return s


async def create(session: AsyncSession, ctx: RequestContext, data: AcademicYearCreate) -> AcademicYear:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    if await repository.get_by_code(session, ctx.school_id, data.code):
        raise ConflictError(
            f"An academic year with code {data.code!r} already exists.",
            code="ACADEMIC_YEAR_CODE_TAKEN",
            details={"code": data.code},
        )

    instance = AcademicYear(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    if instance.is_current:
        await repository.unset_current(session, ctx.school_id, exclude_id=instance.id)

    await audit(
        session, ctx,
        action="ACADEMIC_YEAR_CREATED",
        entity_type="academic_year",
        entity_id=instance.id,
        summary=f"Academic year {instance.code!r} created",
        after=_year_snapshot(instance),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    year: AcademicYear,
    data: AcademicYearUpdate,
) -> AcademicYear:
    if year.version != data.version:
        raise StaleResourceError()

    before = _year_snapshot(year)
    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    for field, value in payload.items():
        setattr(year, field, value)
    year.updated_by_id = ctx.user_id
    await session.flush()

    if payload.get("is_current"):
        await repository.unset_current(session, ctx.school_id, exclude_id=year.id)

    await audit(
        session, ctx,
        action="ACADEMIC_YEAR_UPDATED",
        entity_type="academic_year",
        entity_id=year.id,
        summary=f"Academic year {year.code!r} updated",
        before=before,
        after=_year_snapshot(year),
    )
    return year


async def delete(session: AsyncSession, ctx: RequestContext, year: AcademicYear, version: int) -> None:
    if year.version != version:
        raise StaleResourceError()

    before = _year_snapshot(year)
    year.deleted_at = datetime.now(UTC)
    year.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ACADEMIC_YEAR_DELETED",
        entity_type="academic_year",
        entity_id=year.id,
        summary=f"Academic year {year.code!r} deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, year_id: str) -> AcademicYear:
    if ctx.school_id is None:
        raise NotFoundError("The academic year was not found.", code="ACADEMIC_YEAR_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, year_id)
    if obj is None:
        raise NotFoundError("The academic year was not found.", code="ACADEMIC_YEAR_NOT_FOUND")
    return obj
