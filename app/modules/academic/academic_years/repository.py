"""AcademicYear data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.academic.models import AcademicYear


async def get_by_id(session: AsyncSession, school_id: str, year_id: str) -> AcademicYear | None:
    stmt = select(AcademicYear).where(
        AcademicYear.id == year_id,
        AcademicYear.school_id == school_id,
        AcademicYear.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_code(session: AsyncSession, school_id: str, code: str) -> AcademicYear | None:
    stmt = select(AcademicYear).where(
        AcademicYear.school_id == school_id,
        func.lower(AcademicYear.code) == code.lower(),
        AcademicYear.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def unset_current(session: AsyncSession, school_id: str, exclude_id: str) -> None:
    """Clear is_current on all other years in this school."""
    stmt = (
        update(AcademicYear)
        .where(
            AcademicYear.school_id == school_id,
            AcademicYear.id != exclude_id,
            AcademicYear.is_current.is_(True),
            AcademicYear.deleted_at.is_(None),
        )
        .values(is_current=False)
        .execution_options(synchronize_session="fetch")
    )
    await session.execute(stmt)


async def list_academic_years(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
) -> CursorPage[AcademicYear]:
    stmt = select(AcademicYear).where(
        AcademicYear.school_id == school_id,
        AcademicYear.deleted_at.is_(None),
    )
    return await paginate_cursor(session, stmt, params, model=AcademicYear)
