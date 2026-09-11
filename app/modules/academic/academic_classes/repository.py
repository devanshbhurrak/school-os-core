"""AcademicClass data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.academic.models import AcademicClass


async def get_by_id(session: AsyncSession, school_id: str, academic_class_id: str) -> AcademicClass | None:
    stmt = select(AcademicClass).where(
        AcademicClass.id == academic_class_id,
        AcademicClass.school_id == school_id,
        AcademicClass.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_code(session: AsyncSession, school_id: str, code: str) -> AcademicClass | None:
    stmt = select(AcademicClass).where(
        AcademicClass.school_id == school_id,
        func.lower(AcademicClass.code) == code.lower(),
        AcademicClass.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_academic_classes(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
) -> CursorPage[AcademicClass]:
    stmt = select(AcademicClass).where(
        AcademicClass.school_id == school_id,
        AcademicClass.deleted_at.is_(None),
    )
    return await paginate_cursor(session, stmt, params, model=AcademicClass)
