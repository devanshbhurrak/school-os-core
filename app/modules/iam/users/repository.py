"""User data access.

Users are intentionally NOT tenant-scoped (one account may span schools), so
listing within an organization joins `memberships` — RLS on that join is what
keeps the result scoped to the caller's tenant.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.iam.models import Membership, User


async def get_by_id(session: AsyncSession, user_id: str) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(
        User.email.is_not(None),
        func.lower(User.email) == email.lower(),
        User.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_phone(session: AsyncSession, phone: str) -> User | None:
    stmt = select(User).where(
        User.phone == phone,
        User.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_users_in_org(
    session: AsyncSession,
    organization_id: str,
    params: CursorParams,
) -> CursorPage[User]:
    stmt = (
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.organization_id == organization_id,
            User.deleted_at.is_(None),
        )
        .distinct()
    )
    return await paginate_cursor(session, stmt, params, model=User)


async def belongs_to_org(session: AsyncSession, user_id: str, organization_id: str) -> bool:
    stmt = select(Membership.id).where(
        Membership.user_id == user_id,
        Membership.organization_id == organization_id,
    )
    return (await session.scalars(stmt)).first() is not None
