"""Address data access — org-scoped, queried by polymorphic owner."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.people.models import Address


async def get_by_id(session: AsyncSession, organization_id: str, address_id: str) -> Address | None:
    stmt = select(Address).where(
        Address.id == address_id,
        Address.organization_id == organization_id,
    )
    return (await session.scalars(stmt)).first()


async def list_for_entity(
    session: AsyncSession,
    organization_id: str,
    entity_type: str,
    entity_id: str,
    params: CursorParams,
) -> CursorPage[Address]:
    stmt = select(Address).where(
        Address.organization_id == organization_id,
        Address.entity_type == entity_type,
        Address.entity_id == entity_id,
    )
    return await paginate_cursor(session, stmt, params, model=Address)
