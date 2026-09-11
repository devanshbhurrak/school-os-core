"""User account business logic."""
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
from app.core.hashing import hash_password
from app.modules.iam.enums import MembershipStatus, UserStatus
from app.modules.iam.models import Membership, User
from app.modules.iam.schools import repository as schools_repository
from app.modules.iam.users import repository
from app.modules.iam.users.schemas import UserCreate, UserUpdate
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["email", "phone", "status", "must_change_password", "is_platform_admin"]


async def create(session: AsyncSession, ctx: RequestContext, data: UserCreate) -> User:
    if ctx.organization_id is None:
        raise InvalidRequestError("No organization context is set for this request.")

    if data.email and await repository.get_by_email(session, data.email):
        raise ConflictError(
            "A user with this email already exists.",
            code="USER_EMAIL_TAKEN",
            details={"email": data.email},
        )
    if data.phone and await repository.get_by_phone(session, data.phone):
        raise ConflictError(
            "A user with this phone number already exists.",
            code="USER_PHONE_TAKEN",
            details={"phone": data.phone},
        )

    if data.school_id:
        school = await schools_repository.get_by_id(session, ctx.organization_id, data.school_id)
        if school is None:
            raise NotFoundError("The school was not found.", code="SCHOOL_NOT_FOUND")

    user = User(
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password) if data.password else None,
        status=UserStatus.ACTIVE.value if data.password else UserStatus.INVITED.value,
        password_changed_at=datetime.now(UTC) if data.password else None,
    )
    session.add(user)
    await session.flush()

    membership = Membership(
        user_id=user.id,
        organization_id=ctx.organization_id,
        school_id=data.school_id,
        status=MembershipStatus.ACTIVE.value,
        is_default=True,
        created_by_id=ctx.user_id,
    )
    session.add(membership)
    await session.flush()

    # The response schema exposes memberships; populate it for the in-memory
    # (just-created) instance rather than leaving the selectin relationship lazy.
    await session.refresh(user, attribute_names=["memberships"])

    await audit(
        session, ctx,
        action="USER_CREATED",
        entity_type="user",
        entity_id=user.id,
        summary=f"User {user.email or user.phone} created",
        after=snapshot(user, _SNAPSHOT_FIELDS),
    )
    return user


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    user: User,
    data: UserUpdate,
) -> User:
    if user.version != data.version:
        raise StaleResourceError()

    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    if payload.get("email") and user.email != payload["email"]:  # noqa: SIM102
        if await repository.get_by_email(session, payload["email"]):
            raise ConflictError(
                "A user with this email already exists.",
                code="USER_EMAIL_TAKEN",
                details={"email": payload["email"]},
            )
    if payload.get("phone") and user.phone != payload["phone"]:  # noqa: SIM102
        if await repository.get_by_phone(session, payload["phone"]):
            raise ConflictError(
                "A user with this phone number already exists.",
                code="USER_PHONE_TAKEN",
                details={"phone": payload["phone"]},
            )

    before = snapshot(user, _SNAPSHOT_FIELDS)
    for field, value in payload.items():
        setattr(user, field, value)
    user.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=user.id,
        summary=f"User {user.email or user.phone} updated",
        before=before,
        after=snapshot(user, _SNAPSHOT_FIELDS),
    )
    return user


async def delete(session: AsyncSession, ctx: RequestContext, user: User, version: int) -> None:
    if user.version != version:
        raise StaleResourceError()

    before = snapshot(user, _SNAPSHOT_FIELDS)
    user.deleted_at = datetime.now(UTC)
    await session.flush()

    await audit(
        session, ctx,
        action="USER_DELETED",
        entity_type="user",
        entity_id=user.id,
        summary=f"User {user.email or user.phone} deleted",
        before=before,
    )


async def get_owned(session: AsyncSession, ctx: RequestContext, user_id: str) -> User:
    user = await repository.get_by_id(session, user_id)
    if user is None or user.deleted_at is not None:
        raise NotFoundError("The user was not found.", code="USER_NOT_FOUND")
    if not ctx.is_platform_admin and ctx.organization_id is not None:  # noqa: SIM102
        if not await repository.belongs_to_org(session, user_id, ctx.organization_id):
            raise NotFoundError("The user was not found.", code="USER_NOT_FOUND")
    return user
