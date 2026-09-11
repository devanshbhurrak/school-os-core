"""Organization business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, NotFoundError, StaleResourceError
from app.modules.iam.models import Organization
from app.modules.iam.organizations import repository
from app.modules.iam.organizations.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
)
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = [
    "code", "name", "legal_name", "status", "timezone", "locale",
    "contact_email", "contact_phone", "plan_code",
]


async def create(
    session: AsyncSession,
    ctx: RequestContext,
    data: OrganizationCreate,
) -> Organization:
    if await repository.get_by_code(session, data.code):
        raise ConflictError(
            f"An organization with code {data.code!r} already exists.",
            code="ORGANIZATION_CODE_TAKEN",
            details={"code": data.code},
        )

    instance = Organization(
        code=data.code,
        name=data.name,
        legal_name=data.legal_name,
        timezone=data.timezone,
        locale=data.locale,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        created_by_id=ctx.user_id,
    )
    session.add(instance)
    await session.flush()

    await audit(
        session, ctx,
        action="ORGANIZATION_CREATED",
        entity_type="organization",
        entity_id=instance.id,
        summary=f"Organization {instance.code!r} created",
        organization_id=instance.id,
        after=snapshot(instance, _SNAPSHOT_FIELDS),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    organization: Organization,
    data: OrganizationUpdate,
) -> Organization:
    if organization.version != data.version:
        raise StaleResourceError()

    before = snapshot(organization, _SNAPSHOT_FIELDS)
    for field, value in data.model_dump(exclude={"version"}, exclude_none=True).items():
        setattr(organization, field, value)
    organization.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ORGANIZATION_UPDATED",
        entity_type="organization",
        entity_id=organization.id,
        summary=f"Organization {organization.code!r} updated",
        organization_id=organization.id,
        before=before,
        after=snapshot(organization, _SNAPSHOT_FIELDS),
    )
    return organization


async def delete(
    session: AsyncSession,
    ctx: RequestContext,
    organization: Organization,
    version: int,
) -> None:
    if organization.version != version:
        raise StaleResourceError()

    before = snapshot(organization, _SNAPSHOT_FIELDS)
    organization.deleted_at = datetime.now(UTC)
    organization.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ORGANIZATION_DELETED",
        entity_type="organization",
        entity_id=organization.id,
        summary=f"Organization {organization.code!r} deleted",
        organization_id=organization.id,
        before=before,
    )


async def get_owned(session: AsyncSession, organization_id: str) -> Organization:
    """Fetch a tenant's own organization (RLS guarantees it is theirs)."""
    organization = await repository.get_by_id(session, organization_id)
    if organization is None:
        raise NotFoundError("The organization was not found.", code="ORGANIZATION_NOT_FOUND")
    return organization
