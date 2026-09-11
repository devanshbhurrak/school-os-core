"""Cohort data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.academic.models import Cohort


async def get_by_id(session: AsyncSession, school_id: str, cohort_id: str) -> Cohort | None:
    stmt = select(Cohort).where(
        Cohort.id == cohort_id,
        Cohort.school_id == school_id,
        Cohort.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_code(
    session: AsyncSession, school_id: str, academic_year_id: str, academic_class_id: str, code: str
) -> Cohort | None:
    stmt = select(Cohort).where(
        Cohort.school_id == school_id,
        Cohort.academic_year_id == academic_year_id,
        Cohort.academic_class_id == academic_class_id,
        func.lower(Cohort.code) == code.lower(),
        Cohort.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_cohorts(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    academic_year_id: str | None = None,
    academic_class_id: str | None = None,
) -> CursorPage[Cohort]:
    stmt = select(Cohort).where(
        Cohort.school_id == school_id,
        Cohort.deleted_at.is_(None),
    )
    if academic_year_id:
        stmt = stmt.where(Cohort.academic_year_id == academic_year_id)
    if academic_class_id:
        stmt = stmt.where(Cohort.academic_class_id == academic_class_id)
    return await paginate_cursor(session, stmt, params, model=Cohort)
