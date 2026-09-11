"""AcademicTerm data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.academic.models import AcademicTerm


async def get_by_id(session: AsyncSession, school_id: str, term_id: str) -> AcademicTerm | None:
    stmt = select(AcademicTerm).where(
        AcademicTerm.id == term_id,
        AcademicTerm.school_id == school_id,
        AcademicTerm.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_code(
    session: AsyncSession, school_id: str, academic_year_id: str, code: str
) -> AcademicTerm | None:
    stmt = select(AcademicTerm).where(
        AcademicTerm.school_id == school_id,
        AcademicTerm.academic_year_id == academic_year_id,
        func.lower(AcademicTerm.code) == code.lower(),
        AcademicTerm.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_academic_terms(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    academic_year_id: str | None = None,
) -> CursorPage[AcademicTerm]:
    stmt = select(AcademicTerm).where(
        AcademicTerm.school_id == school_id,
        AcademicTerm.deleted_at.is_(None),
    )
    if academic_year_id:
        stmt = stmt.where(AcademicTerm.academic_year_id == academic_year_id)
    return await paginate_cursor(session, stmt, params, model=AcademicTerm)
