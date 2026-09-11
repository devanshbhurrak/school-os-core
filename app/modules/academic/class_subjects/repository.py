"""ClassSubject data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.academic.models import ClassSubject


async def get_by_id(session: AsyncSession, school_id: str, class_subject_id: str) -> ClassSubject | None:
    stmt = select(ClassSubject).where(
        ClassSubject.id == class_subject_id,
        ClassSubject.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()


async def get_existing(
    session: AsyncSession, school_id: str, academic_class_id: str, subject_id: str
) -> ClassSubject | None:
    stmt = select(ClassSubject).where(
        ClassSubject.school_id == school_id,
        ClassSubject.academic_class_id == academic_class_id,
        ClassSubject.subject_id == subject_id,
    )
    return (await session.scalars(stmt)).first()


async def list_class_subjects(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    academic_class_id: str | None = None,
    year_id: str | None = None,
) -> CursorPage[ClassSubject]:
    stmt = select(ClassSubject).where(ClassSubject.school_id == school_id)
    if academic_class_id:
        stmt = stmt.where(ClassSubject.academic_class_id == academic_class_id)
    if year_id:
        stmt = stmt.where(ClassSubject.effective_from_year_id == year_id)
    return await paginate_cursor(session, stmt, params, model=ClassSubject)
