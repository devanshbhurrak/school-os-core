"""AcademicTerm business logic."""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.academic.academic_terms import repository
from app.modules.academic.academic_terms.schemas import AcademicTermCreate, AcademicTermUpdate
from app.modules.academic.models import AcademicTerm, AcademicYear
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["code", "name", "status", "academic_year_id"]


def _term_snapshot(term) -> dict:
    s = snapshot(term, _SNAPSHOT_FIELDS)
    s["start_date"] = str(term.start_date) if term.start_date else None
    s["end_date"] = str(term.end_date) if term.end_date else None
    return s


async def _get_year(session: AsyncSession, school_id: str, year_id: str) -> AcademicYear:
    from sqlalchemy import select
    stmt = select(AcademicYear).where(
        AcademicYear.id == year_id,
        AcademicYear.school_id == school_id,
        AcademicYear.deleted_at.is_(None),
    )
    obj = (await session.scalars(stmt)).first()
    if obj is None:
        raise NotFoundError("The academic year was not found.", code="ACADEMIC_YEAR_NOT_FOUND")
    return obj


def _validate_term_dates(term_start: date, term_end: date, year_start: date, year_end: date) -> None:
    if term_start < year_start or term_end > year_end:
        raise InvalidRequestError(
            "Term dates must fall within the academic year date range."
        )
    if term_end < term_start:
        raise InvalidRequestError("Term end date must be on or after the start date.")


async def create(session: AsyncSession, ctx: RequestContext, data: AcademicTermCreate) -> AcademicTerm:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    year = await _get_year(session, ctx.school_id, data.academic_year_id)
    _validate_term_dates(data.start_date, data.end_date, year.start_date, year.end_date)

    if await repository.get_by_code(session, ctx.school_id, data.academic_year_id, data.code):
        raise ConflictError(
            f"A term with code {data.code!r} already exists in this academic year.",
            code="ACADEMIC_TERM_CODE_TAKEN",
            details={"code": data.code},
        )

    instance = AcademicTerm(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="ACADEMIC_TERM_CREATED",
        entity_type="academic_term",
        entity_id=instance.id,
        summary=f"Academic term {instance.code!r} created",
        after=_term_snapshot(instance),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    term: AcademicTerm,
    data: AcademicTermUpdate,
) -> AcademicTerm:
    if term.version != data.version:
        raise StaleResourceError()

    payload = data.model_dump(exclude={"version"}, exclude_none=True)

    # Validate dates against parent year if any date is being changed
    new_start = payload.get("start_date", term.start_date)
    new_end = payload.get("end_date", term.end_date)
    year = await _get_year(session, ctx.school_id, term.academic_year_id)
    _validate_term_dates(new_start, new_end, year.start_date, year.end_date)

    before = _term_snapshot(term)
    for field, value in payload.items():
        setattr(term, field, value)
    term.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ACADEMIC_TERM_UPDATED",
        entity_type="academic_term",
        entity_id=term.id,
        summary=f"Academic term {term.code!r} updated",
        before=before,
        after=_term_snapshot(term),
    )
    return term


async def delete(session: AsyncSession, ctx: RequestContext, term: AcademicTerm, version: int) -> None:
    if term.version != version:
        raise StaleResourceError()

    before = _term_snapshot(term)
    term.deleted_at = datetime.now(UTC)
    term.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ACADEMIC_TERM_DELETED",
        entity_type="academic_term",
        entity_id=term.id,
        summary=f"Academic term {term.code!r} deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, term_id: str) -> AcademicTerm:
    if ctx.school_id is None:
        raise NotFoundError("The academic term was not found.", code="ACADEMIC_TERM_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, term_id)
    if obj is None:
        raise NotFoundError("The academic term was not found.", code="ACADEMIC_TERM_NOT_FOUND")
    return obj
