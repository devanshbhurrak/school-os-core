"""Student data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.people.models import Person
from app.modules.students.enums import StudentStatus
from app.modules.students.models import Student


async def get_by_id(session: AsyncSession, school_id: str, student_id: str) -> Student | None:
    stmt = (
        select(Student)
        .options(selectinload(Student.person))
        .where(
            Student.id == student_id,
            Student.school_id == school_id,
            Student.deleted_at.is_(None),
        )
    )
    return (await session.scalars(stmt)).first()


async def get_by_admission_number(
    session: AsyncSession, school_id: str, admission_number: str
) -> Student | None:
    stmt = select(Student).where(
        Student.school_id == school_id,
        Student.admission_number == admission_number,
        Student.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def get_by_person_id(
    session: AsyncSession, school_id: str, person_id: str
) -> Student | None:
    stmt = select(Student).where(
        Student.school_id == school_id,
        Student.person_id == person_id,
        Student.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_students(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    search: str | None = None,
    status: StudentStatus | None = None,
) -> CursorPage[Student]:
    stmt = (
        select(Student)
        .options(selectinload(Student.person))
        .join(Person, Student.person_id == Person.id)
        .where(
            Student.school_id == school_id,
            Student.deleted_at.is_(None),
        )
    )
    if status is not None:
        stmt = stmt.where(Student.status == status.value)
    if search:
        pattern = f"%{search.strip().lower()}%"
        full_name = func.lower(
            func.concat_ws(" ", Person.first_name, Person.last_name)
        )
        stmt = stmt.where(
            (full_name.like(pattern))
            | (Student.admission_number.ilike(pattern))
        )
    return await paginate_cursor(session, stmt, params, model=Student)
