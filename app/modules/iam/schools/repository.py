"""School data access — always scoped to an organization."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.iam.models import School


async def get_by_id(session: AsyncSession, organization_id: str, school_id: str) -> School | None:
    stmt = select(School).where(
        School.id == school_id,
        School.organization_id == organization_id,
        School.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_code(session: AsyncSession, organization_id: str, code: str) -> School | None:
    stmt = select(School).where(
        School.organization_id == organization_id,
        func.lower(School.code) == code.lower(),
        School.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_schools(
    session: AsyncSession,
    organization_id: str,
    params: CursorParams,
    *,
    status: str | None = None,
) -> CursorPage[School]:
    stmt = select(School).where(
        School.organization_id == organization_id,
        School.deleted_at.is_(None),
    )
    if status:
        stmt = stmt.where(School.status == status)
    return await paginate_cursor(session, stmt, params, model=School)


async def list_all_schools(
    session: AsyncSession,
    params: CursorParams,
    *,
    organization_id: str | None = None,
    status: str | None = None,
) -> CursorPage[School]:
    """Return schools across all orgs. Platform admins only (enforced at router)."""
    stmt = select(School).where(School.deleted_at.is_(None))
    if organization_id:
        stmt = stmt.where(School.organization_id == organization_id)
    if status:
        stmt = stmt.where(School.status == status)
    return await paginate_cursor(session, stmt, params, model=School)
