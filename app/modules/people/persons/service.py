"""Person business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    StaleResourceError,
)
from app.modules.people.enums import PersonStatus
from app.modules.people.models import Person
from app.modules.people.persons import repository
from app.modules.people.persons.schemas import PersonCreate, PersonMerge, PersonUpdate
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = [
    "first_name", "middle_name", "last_name", "preferred_name", "date_of_birth",
    "gender", "blood_group", "nationality", "primary_phone", "primary_email",
    "address_id", "status",
]


async def create(session: AsyncSession, ctx: RequestContext, data: PersonCreate) -> Person:
    if ctx.organization_id is None:
        raise InvalidRequestError("No organization context is set for this request.")

    if data.address_id:
        await _assert_address_owned(session, ctx, data.address_id)

    instance = Person(
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="PERSON_CREATED",
        entity_type="person",
        entity_id=instance.id,
        summary=f"Person {instance.first_name} {instance.last_name or ''}".rstrip(),
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    person: Person,
    data: PersonUpdate,
) -> Person:
    if person.version != data.version:
        raise StaleResourceError()

    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    if payload.get("address_id"):
        await _assert_address_owned(session, ctx, payload["address_id"])

    before = snapshot(person, _SNAPSHOT_FIELDS)
    for field, value in payload.items():
        setattr(person, field, value)
    person.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="PERSON_UPDATED",
        entity_type="person",
        entity_id=person.id,
        summary="Person updated",
        before=before,
        after=snapshot(person, _SNAPSHOT_FIELDS),
    )
    return person


async def delete(session: AsyncSession, ctx: RequestContext, person: Person, version: int) -> None:
    if person.version != version:
        raise StaleResourceError()

    before = snapshot(person, _SNAPSHOT_FIELDS)
    person.deleted_at = datetime.now(UTC)
    person.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="PERSON_DELETED",
        entity_type="person",
        entity_id=person.id,
        summary="Person deleted",
        before=before,
    )


async def merge(
    session: AsyncSession,
    ctx: RequestContext,
    person: Person,
    data: PersonMerge,
) -> Person:
    """Merge `person` into `target`: mark MERGED, point at target."""
    if person.version != data.version:
        raise StaleResourceError()
    if person.id == data.target_person_id:
        raise ConflictError("A person cannot be merged into itself.", code="PERSON_MERGE_SELF")

    target = await repository.get_by_id(session, ctx.organization_id, data.target_person_id)
    if target is None:
        raise NotFoundError("The target person was not found.", code="PERSON_NOT_FOUND")

    before = snapshot(person, _SNAPSHOT_FIELDS)
    person.status = PersonStatus.MERGED.value
    person.merged_into_person_id = target.id
    person.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="PERSON_MERGED",
        entity_type="person",
        entity_id=person.id,
        summary=f"Person merged into {target.id}",
        before=before,
        after=snapshot(person, _SNAPSHOT_FIELDS),
    )
    return person


async def get_owned(session: AsyncSession, ctx: RequestContext, person_id: str) -> Person:
    if ctx.organization_id is None:
        raise NotFoundError("The person was not found.", code="PERSON_NOT_FOUND")
    person = await repository.get_by_id(session, ctx.organization_id, person_id)
    if person is None:
        raise NotFoundError("The person was not found.", code="PERSON_NOT_FOUND")
    return person


async def _assert_address_owned(session: AsyncSession, ctx: RequestContext, address_id: str) -> None:
    from app.modules.people.addresses import repository as addresses_repository

    address = await addresses_repository.get_by_id(session, ctx.organization_id, address_id)
    if address is None:
        raise NotFoundError("The address was not found.", code="ADDRESS_NOT_FOUND")
