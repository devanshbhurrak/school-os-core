"""Contact data access — org-scoped, queried by polymorphic owner."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.people.models import Contact


async def get_by_id(session: AsyncSession, organization_id: str, contact_id: str) -> Contact | None:
    stmt = select(Contact).where(
        Contact.id == contact_id,
        Contact.organization_id == organization_id,
    )
    return (await session.scalars(stmt)).first()


async def list_for_entity(
    session: AsyncSession,
    organization_id: str,
    entity_type: str,
    entity_id: str,
    params: CursorParams,
) -> CursorPage[Contact]:
    stmt = select(Contact).where(
        Contact.organization_id == organization_id,
        Contact.entity_type == entity_type,
        Contact.entity_id == entity_id,
    )
    return await paginate_cursor(session, stmt, params, model=Contact)
