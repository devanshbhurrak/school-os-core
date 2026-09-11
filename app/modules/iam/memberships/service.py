"""Membership business logic: user → school → roles."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidRequestError,
    NotFoundError,
    StaleResourceError,
)
from app.modules.iam.enums import MembershipStatus
from app.modules.iam.memberships import repository
from app.modules.iam.memberships.schemas import (
    MembershipCreate,
    MembershipUpdate,
    RoleGrantCreate,
)
from app.modules.iam.models import Membership, MembershipRole
from app.modules.iam.roles import repository as roles_repository
from app.modules.iam.schools import repository as schools_repository
from app.modules.iam.users import repository as users_repository
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["user_id", "organization_id", "school_id", "status", "start_date", "end_date", "is_default"]


async def create(session: AsyncSession, ctx: RequestContext, data: MembershipCreate) -> Membership:
    if ctx.organization_id is None:
        raise InvalidRequestError("No organization context is set for this request.")

    user = await users_repository.get_by_id(session, data.user_id)
    if user is None or user.deleted_at is not None:
        raise NotFoundError("The user was not found.", code="USER_NOT_FOUND")

    if data.school_id:
        school = await schools_repository.get_by_id(session, ctx.organization_id, data.school_id)
        if school is None:
            raise NotFoundError("The school was not found.", code="SCHOOL_NOT_FOUND")

    existing = await repository.get_active_for_user_school(
        session, data.user_id, ctx.organization_id, data.school_id
    )
    if existing:
        raise ConflictError(
            "The user already has a membership for this school.",
            code="MEMBERSHIP_EXISTS",
            details={"membership_id": existing.id},
        )

    memberships = Membership(
        user_id=data.user_id,
        organization_id=ctx.organization_id,
        school_id=data.school_id,
        status=MembershipStatus.ACTIVE.value,
        start_date=data.start_date,
        end_date=data.end_date,
        is_default=data.is_default,
        created_by_id=ctx.user_id,
    )
    session.add(memberships)
    await session.flush()

    for role_id in data.role_ids:
        role = await roles_repository.get_org_role(session, ctx.organization_id, role_id)
        if role is None or role.archived_at is not None:
            raise NotFoundError("A requested role was not found.", code="ROLE_NOT_FOUND")
        session.add(
            MembershipRole(
                membership_id=memberships.id,
                role_id=role.id,
                created_by_id=ctx.user_id,
            )
        )
    await session.flush()

    # The response schema exposes role_codes; populate the in-memory instance.
    await session.refresh(memberships, attribute_names=["role_links"])

    await audit(
        session, ctx,
        action="MEMBERSHIP_CREATED",
        entity_type="membership",
        entity_id=memberships.id,
        summary=f"Membership created for user {data.user_id}",
        after=snapshot(memberships, _SNAPSHOT_FIELDS),
    )
    return memberships


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    membership: Membership,
    data: MembershipUpdate,
) -> Membership:
    if membership.version != data.version:
        raise StaleResourceError()

    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    before = snapshot(membership, _SNAPSHOT_FIELDS)
    for field, value in payload.items():
        setattr(membership, field, value)
    membership.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="MEMBERSHIP_UPDATED",
        entity_type="membership",
        entity_id=membership.id,
        summary="Membership updated",
        before=before,
        after=snapshot(membership, _SNAPSHOT_FIELDS),
    )
    return membership


async def end(session: AsyncSession, ctx: RequestContext, membership: Membership, version: int) -> None:
    """End a membership today: status ENDED, end_date today (time-bounded truth)."""
    if membership.version != version:
        raise StaleResourceError()

    before = snapshot(membership, _SNAPSHOT_FIELDS)
    membership.status = MembershipStatus.ENDED.value
    membership.end_date = date.today()
    membership.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="MEMBERSHIP_ENDED",
        entity_type="membership",
        entity_id=membership.id,
        summary="Membership ended",
        before=before,
        after=snapshot(membership, _SNAPSHOT_FIELDS),
    )


async def grant_role(
    session: AsyncSession,
    ctx: RequestContext,
    membership: Membership,
    data: RoleGrantCreate,
) -> MembershipRole:
    role = await roles_repository.get_org_role(session, membership.organization_id, data.role_id)
    if role is None or role.archived_at is not None:
        raise NotFoundError("The role was not found.", code="ROLE_NOT_FOUND")
    if role.is_system and role.organization_id is None and role.scope_level == "PLATFORM":
        raise ForbiddenError("This role cannot be granted.")

    existing = await session.scalar(
        select(MembershipRole).where(
            MembershipRole.membership_id == membership.id,
            MembershipRole.role_id == role.id,
        )
    )
    if existing:
        raise ConflictError(
            "The role is already granted on this membership.",
            code="ROLE_ALREADY_GRANTED",
            details={"role_id": role.id},
        )

    link = MembershipRole(
        membership_id=membership.id,
        role_id=role.id,
        expires_at=data.expires_at,
        data_scope=data.data_scope.value if data.data_scope else None,
        created_by_id=ctx.user_id,
    )
    session.add(link)
    await session.flush()

    await audit(
        session, ctx,
        action="ROLE_GRANTED",
        entity_type="membership_role",
        entity_id=link.id,
        summary=f"Role {role.code!r} granted",
    )
    return link


async def revoke_role(
    session: AsyncSession,
    ctx: RequestContext,
    membership: Membership,
    role_id: str,
) -> None:
    link = await session.scalar(
        select(MembershipRole).where(
            MembershipRole.membership_id == membership.id,
            MembershipRole.role_id == role_id,
        )
    )
    if link is None:
        raise NotFoundError("The role grant was not found.", code="ROLE_GRANT_NOT_FOUND")

    await session.delete(link)
    await session.flush()

    await audit(
        session, ctx,
        action="ROLE_REVOKED",
        entity_type="membership_role",
        entity_id=link.id,
        summary=f"Role {role_id} revoked",
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, membership_id: str) -> Membership:
    if ctx.organization_id is None:
        raise NotFoundError("The membership was not found.", code="MEMBERSHIP_NOT_FOUND")
    membership = await repository.get_by_id(session, ctx.organization_id, membership_id)
    if membership is None:
        raise NotFoundError("The membership was not found.", code="MEMBERSHIP_NOT_FOUND")
    return membership
