"""Address business logic."""
from __future__ import annotations

from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.people.addresses import repository
from app.modules.people.addresses.schemas import (
    ALLOWED_ENTITY_TYPES,
    AddressCreate,
    AddressUpdate,
)
from app.modules.people.models import Address
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = [
    "entity_type", "entity_id", "address_type", "line1", "line2", "landmark",
    "city", "district", "state", "postal_code", "country_code", "is_primary",
]


async def create(session: AsyncSession, ctx: RequestContext, data: AddressCreate) -> Address:
    if ctx.organization_id is None:
        raise InvalidRequestError("No organization context is set for this request.")
    if data.entity_type not in ALLOWED_ENTITY_TYPES:
        raise InvalidRequestError(
            f"Unsupported entity_type {data.entity_type!r}. Allowed: {', '.join(ALLOWED_ENTITY_TYPES)}.",
            code="UNSUPPORTED_ENTITY_TYPE",
        )
    await _assert_entity_owned(session, ctx, data.entity_type, data.entity_id)

    instance = Address(
        organization_id=ctx.organization_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        address_type=data.address_type.value,
        line1=data.line1,
        line2=data.line2,
        landmark=data.landmark,
        city=data.city,
        district=data.district,
        state=data.state,
        postal_code=data.postal_code,
        country_code=data.country_code,
        is_primary=data.is_primary,
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="ADDRESS_CREATED",
        entity_type="address",
        entity_id=instance.id,
        summary=f"Address created for {data.entity_type} {data.entity_id}",
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    address: Address,
    data: AddressUpdate,
) -> Address:
    if address.version != data.version:
        raise StaleResourceError()

    before = snapshot(address, _SNAPSHOT_FIELDS)
    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    for field, value in payload.items():
        setattr(address, field, value.value if hasattr(value, "value") else value)
    await session.flush()

    await audit(
        session, ctx,
        action="ADDRESS_UPDATED",
        entity_type="address",
        entity_id=address.id,
        summary="Address updated",
        before=before,
        after=snapshot(address, _SNAPSHOT_FIELDS),
    )
    return address


async def delete(session: AsyncSession, ctx: RequestContext, address: Address, version: int) -> None:
    if address.version != version:
        raise StaleResourceError()

    before = snapshot(address, _SNAPSHOT_FIELDS)
    await session.execute(
        sa_delete(Address).where(Address.id == address.id, Address.organization_id == ctx.organization_id)
    )
    await session.flush()

    await audit(
        session, ctx,
        action="ADDRESS_DELETED",
        entity_type="address",
        entity_id=address.id,
        summary="Address deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, address_id: str) -> Address:
    if ctx.organization_id is None:
        raise NotFoundError("The address was not found.", code="ADDRESS_NOT_FOUND")
    address = await repository.get_by_id(session, ctx.organization_id, address_id)
    if address is None:
        raise NotFoundError("The address was not found.", code="ADDRESS_NOT_FOUND")
    return address


async def _assert_entity_owned(
    session: AsyncSession, ctx: RequestContext, entity_type: str, entity_id: str
) -> None:
    if entity_type == "SCHOOL":
        from app.modules.iam.schools import repository as schools_repository

        school = await schools_repository.get_by_id(session, ctx.organization_id, entity_id)
        if school is None:
            raise NotFoundError("The owning school was not found.", code="SCHOOL_NOT_FOUND")
    elif entity_type == "PERSON":
        from app.modules.people.persons import repository as persons_repository

        person = await persons_repository.get_by_id(session, ctx.organization_id, entity_id)
        if person is None:
            raise NotFoundError("The owning person was not found.", code="PERSON_NOT_FOUND")
