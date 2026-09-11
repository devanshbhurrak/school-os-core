"""Cohort business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.academic.academic_classes import repository as classes_repository
from app.modules.academic.academic_years import repository as years_repository
from app.modules.academic.cohorts import repository
from app.modules.academic.cohorts.schemas import CohortCreate, CohortUpdate
from app.modules.academic.models import Cohort
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["code", "name", "capacity", "status", "academic_year_id", "academic_class_id"]


async def create(session: AsyncSession, ctx: RequestContext, data: CohortCreate) -> Cohort:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    if not await years_repository.get_by_id(session, ctx.school_id, data.academic_year_id):
        raise NotFoundError("The academic year was not found.", code="ACADEMIC_YEAR_NOT_FOUND")

    if not await classes_repository.get_by_id(session, ctx.school_id, data.academic_class_id):
        raise NotFoundError("The academic class was not found.", code="ACADEMIC_CLASS_NOT_FOUND")

    if await repository.get_by_code(
        session, ctx.school_id, data.academic_year_id, data.academic_class_id, data.code
    ):
        raise ConflictError(
            f"A cohort with code {data.code!r} already exists for this class and year.",
            code="COHORT_CODE_TAKEN",
            details={"code": data.code},
        )

    instance = Cohort(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="COHORT_CREATED",
        entity_type="cohort",
        entity_id=instance.id,
        summary=f"Cohort {instance.code!r} created",
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    cohort: Cohort,
    data: CohortUpdate,
) -> Cohort:
    if cohort.version != data.version:
        raise StaleResourceError()

    before = snapshot(cohort, _SNAPSHOT_FIELDS)
    for field, value in data.model_dump(exclude={"version"}, exclude_none=True).items():
        setattr(cohort, field, value)
    cohort.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="COHORT_UPDATED",
        entity_type="cohort",
        entity_id=cohort.id,
        summary=f"Cohort {cohort.code!r} updated",
        before=before,
        after=snapshot(cohort, _SNAPSHOT_FIELDS),
    )
    return cohort


async def delete(session: AsyncSession, ctx: RequestContext, cohort: Cohort, version: int) -> None:
    if cohort.version != version:
        raise StaleResourceError()

    before = snapshot(cohort, _SNAPSHOT_FIELDS)
    cohort.deleted_at = datetime.now(UTC)
    cohort.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="COHORT_DELETED",
        entity_type="cohort",
        entity_id=cohort.id,
        summary=f"Cohort {cohort.code!r} deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, cohort_id: str) -> Cohort:
    if ctx.school_id is None:
        raise NotFoundError("The cohort was not found.", code="COHORT_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, cohort_id)
    if obj is None:
        raise NotFoundError("The cohort was not found.", code="COHORT_NOT_FOUND")
    return obj
