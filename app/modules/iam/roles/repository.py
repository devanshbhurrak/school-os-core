"""Role data access — org roles plus the always-visible system roles."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.iam.models import Role


async def get_by_id(session: AsyncSession, role_id: str) -> Role | None:
    return await session.get(Role, role_id)


async def get_org_role(session: AsyncSession, organization_id: str, role_id: str) -> Role | None:
    """Fetch a role the caller's org owns; system roles are also reachable."""
    stmt = select(Role).where(
        Role.id == role_id,
        Role.archived_at.is_(None),
        or_(Role.organization_id == organization_id, Role.organization_id.is_(None)),
    )
    return (await session.scalars(stmt)).first()


async def get_by_code(session: AsyncSession, organization_id: str, code: str) -> Role | None:
    stmt = select(Role).where(
        func.lower(Role.code) == code.lower(),
        Role.archived_at.is_(None),
        or_(Role.organization_id == organization_id, Role.organization_id.is_(None)),
    )
    return (await session.scalars(stmt)).first()


async def list_roles(session: AsyncSession, organization_id: str, params: CursorParams) -> CursorPage[Role]:
    stmt = select(Role).where(
        Role.archived_at.is_(None),
        or_(Role.organization_id == organization_id, Role.organization_id.is_(None)),
    )
    return await paginate_cursor(session, stmt, params, model=Role)
