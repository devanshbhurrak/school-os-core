"""Contact business logic."""
from __future__ import annotations

from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError
from app.modules.people.contacts import repository
from app.modules.people.contacts.schemas import (
    ALLOWED_ENTITY_TYPES,
    ContactCreate,
    ContactUpdate,
)
from app.modules.people.models import Contact
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["entity_type", "entity_id", "contact_type", "value", "label", "is_primary", "is_emergency"]


async def create(session: AsyncSession, ctx: RequestContext, data: ContactCreate) -> Contact:
    if ctx.organization_id is None:
        raise InvalidRequestError("No organization context is set for this request.")
    if data.entity_type not in ALLOWED_ENTITY_TYPES:
        raise InvalidRequestError(
            f"Unsupported entity_type {data.entity_type!r}. Allowed: {', '.join(ALLOWED_ENTITY_TYPES)}.",
            code="UNSUPPORTED_ENTITY_TYPE",
        )
    await _assert_entity_owned(session, ctx, data.entity_type, data.entity_id)

    if await _exists(session, ctx.organization_id, data):
        raise ConflictError(
            "This contact already exists for the entity.",
            code="CONTACT_EXISTS",
            details={"value": data.value, "contact_type": data.contact_type.value},
        )

    instance = Contact(
        organization_id=ctx.organization_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        contact_type=data.contact_type.value,
        value=data.value,
        label=data.label,
        is_primary=data.is_primary,
        is_emergency=data.is_emergency,
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="CONTACT_CREATED",
        entity_type="contact",
        entity_id=instance.id,
        summary=f"Contact created for {data.entity_type} {data.entity_id}",
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    contact: Contact,
    data: ContactUpdate,
) -> Contact:
    before = snapshot(contact, _SNAPSHOT_FIELDS)
    payload = data.model_dump(exclude_none=True)
    for field, value in payload.items():
        setattr(contact, field, value.value if hasattr(value, "value") else value)
    await session.flush()

    await audit(
        session, ctx,
        action="CONTACT_UPDATED",
        entity_type="contact",
        entity_id=contact.id,
        summary="Contact updated",
        before=before,
        after=snapshot(contact, _SNAPSHOT_FIELDS),
    )
    return contact


async def delete(session: AsyncSession, ctx: RequestContext, contact: Contact) -> None:
    before = snapshot(contact, _SNAPSHOT_FIELDS)
    await session.execute(
        sa_delete(Contact).where(Contact.id == contact.id, Contact.organization_id == ctx.organization_id)
    )
    await session.flush()

    await audit(
        session, ctx,
        action="CONTACT_DELETED",
        entity_type="contact",
        entity_id=contact.id,
        summary="Contact deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, contact_id: str) -> Contact:
    if ctx.organization_id is None:
        raise NotFoundError("The contact was not found.", code="CONTACT_NOT_FOUND")
    contact = await repository.get_by_id(session, ctx.organization_id, contact_id)
    if contact is None:
        raise NotFoundError("The contact was not found.", code="CONTACT_NOT_FOUND")
    return contact


async def _exists(session: AsyncSession, organization_id: str, data: ContactCreate) -> bool:
    from sqlalchemy import select

    stmt = select(Contact.id).where(
        Contact.organization_id == organization_id,
        Contact.entity_type == data.entity_type,
        Contact.entity_id == data.entity_id,
        Contact.contact_type == data.contact_type.value,
        Contact.value == data.value,
    )
    return (await session.scalars(stmt)).first() is not None


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
