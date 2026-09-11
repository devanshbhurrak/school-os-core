"""Person data access — org-scoped, with trigram-backed name search."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.people.models import Person


async def get_by_id(session: AsyncSession, organization_id: str, person_id: str) -> Person | None:
    stmt = select(Person).where(
        Person.id == person_id,
        Person.organization_id == organization_id,
        Person.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_persons(
    session: AsyncSession,
    organization_id: str,
    params: CursorParams,
    *,
    search: str | None = None,
) -> CursorPage[Person]:
    stmt = select(Person).where(
        Person.organization_id == organization_id,
        Person.deleted_at.is_(None),
    )
    if search:
        pattern = f"%{search.strip().lower()}%"
        full_name = func.lower(
            func.concat_ws(" ", Person.first_name, Person.middle_name, Person.last_name)
        )
        stmt = stmt.where(
            (full_name.like(pattern))
            | (Person.primary_email.is_not(None) & func.lower(Person.primary_email).like(pattern))
            | (Person.primary_phone.is_not(None) & Person.primary_phone.like(pattern))
        )
    return await paginate_cursor(session, stmt, params, model=Person)
