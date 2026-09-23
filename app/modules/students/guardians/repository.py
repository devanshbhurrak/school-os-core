"""Guardian data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.students.models import StudentGuardian


async def get_by_id(
    session: AsyncSession, id: str, school_id: str
) -> StudentGuardian | None:
    stmt = (
        select(StudentGuardian)
        .options(selectinload(StudentGuardian.guardian_person))
        .where(
            StudentGuardian.id == id,
            StudentGuardian.school_id == school_id,
        )
    )
    return (await session.scalars(stmt)).first()


async def list_for_student(
    session: AsyncSession, student_id: str, school_id: str
) -> list[StudentGuardian]:
    stmt = (
        select(StudentGuardian)
        .options(selectinload(StudentGuardian.guardian_person))
        .where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.school_id == school_id,
        )
        .order_by(StudentGuardian.is_primary.desc())
    )
    return list((await session.scalars(stmt)).all())


async def get_by_student_and_person(
    session: AsyncSession,
    student_id: str,
    guardian_person_id: str,
    school_id: str,
) -> StudentGuardian | None:
    stmt = select(StudentGuardian).where(
        StudentGuardian.student_id == student_id,
        StudentGuardian.guardian_person_id == guardian_person_id,
        StudentGuardian.school_id == school_id,
    )
    return (await session.scalars(stmt)).first()
