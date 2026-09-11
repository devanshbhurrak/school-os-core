"""Organization data access — every query carries an explicit tenant scope."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.iam.models import Organization


async def get_by_id(session: AsyncSession, organization_id: str) -> Organization | None:
    stmt = select(Organization).where(
        Organization.id == organization_id,
        Organization.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_code(session: AsyncSession, code: str) -> Organization | None:
    stmt = select(Organization).where(
        func.lower(Organization.code) == code.lower(),
        Organization.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_organizations(
    session: AsyncSession,
    params: CursorParams,
) -> CursorPage[Organization]:
    stmt = select(Organization).where(Organization.deleted_at.is_(None))
    return await paginate_cursor(session, stmt, params, model=Organization)
