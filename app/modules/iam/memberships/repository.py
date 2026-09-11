"""Membership data access — scoped to an organization via RLS."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.iam.models import Membership


async def get_by_id(session: AsyncSession, organization_id: str, membership_id: str) -> Membership | None:
    stmt = select(Membership).where(
        Membership.id == membership_id,
        Membership.organization_id == organization_id,
    )
    return (await session.scalars(stmt)).first()


async def list_memberships(
    session: AsyncSession,
    organization_id: str,
    params: CursorParams,
    *,
    school_id: str | None = None,
    user_id: str | None = None,
) -> CursorPage[Membership]:
    stmt = select(Membership).where(Membership.organization_id == organization_id)
    if school_id:
        stmt = stmt.where(Membership.school_id == school_id)
    if user_id:
        stmt = stmt.where(Membership.user_id == user_id)
    return await paginate_cursor(session, stmt, params, model=Membership)


async def get_active_for_user_school(
    session: AsyncSession,
    user_id: str,
    organization_id: str,
    school_id: str | None,
) -> Membership | None:
    stmt = select(Membership).where(
        Membership.user_id == user_id,
        Membership.organization_id == organization_id,
        Membership.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()
