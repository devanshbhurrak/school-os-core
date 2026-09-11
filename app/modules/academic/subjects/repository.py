"""Subject data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.academic.models import Subject


async def get_by_id(session: AsyncSession, school_id: str, subject_id: str) -> Subject | None:
    stmt = select(Subject).where(
        Subject.id == subject_id,
        Subject.school_id == school_id,
        Subject.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_code(session: AsyncSession, school_id: str, code: str) -> Subject | None:
    stmt = select(Subject).where(
        Subject.school_id == school_id,
        func.lower(Subject.code) == code.lower(),
        Subject.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_subjects(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
) -> CursorPage[Subject]:
    stmt = select(Subject).where(
        Subject.school_id == school_id,
        Subject.deleted_at.is_(None),
    )
    return await paginate_cursor(session, stmt, params, model=Subject)
