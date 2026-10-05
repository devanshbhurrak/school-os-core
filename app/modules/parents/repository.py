"""Parent data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.parents.enums import ParentStatus
from app.modules.parents.models import Parent, StudentParent
from app.modules.people.models import Person
from app.modules.students.models import Student


async def get_by_id(session: AsyncSession, school_id: str, parent_id: str) -> Parent | None:
    stmt = (
        select(Parent)
        .options(selectinload(Parent.person))
        .where(
            Parent.id == parent_id,
            Parent.school_id == school_id,
            Parent.deleted_at.is_(None),
        )
    )
    return (await session.scalars(stmt)).first()


async def get_by_person_id(
    session: AsyncSession, school_id: str, person_id: str
) -> Parent | None:
    stmt = select(Parent).where(
        Parent.school_id == school_id,
        Parent.person_id == person_id,
        Parent.deleted_at.is_(None),
    )
    return (await session.scalars(stmt)).first()


async def list_parents(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    *,
    search: str | None = None,
    status: ParentStatus | None = None,
) -> CursorPage[Parent]:
    stmt = (
        select(Parent)
        .options(selectinload(Parent.person))
        .join(Person, Parent.person_id == Person.id)
        .where(
            Parent.school_id == school_id,
            Parent.deleted_at.is_(None),
        )
    )
    if status is not None:
        stmt = stmt.where(Parent.status == status.value)
    if search:
        pattern = f"%{search.strip().lower()}%"
        full_name = func.lower(
            func.concat_ws(" ", Person.first_name, Person.last_name)
        )
        stmt = stmt.where(full_name.like(pattern))
    return await paginate_cursor(session, stmt, params, model=Parent)


async def list_children(
    session: AsyncSession, parent_id: str, school_id: str
) -> list[StudentParent]:
    stmt = (
        select(StudentParent)
        .join(Student, StudentParent.student_id == Student.id)
        .options(
            selectinload(StudentParent.student).selectinload(Student.person),
        )
        .where(
            StudentParent.parent_id == parent_id,
            Student.school_id == school_id,
            Student.deleted_at.is_(None),
        )
    )
    return list((await session.scalars(stmt)).all())


async def list_parents_for_student(
    session: AsyncSession, student_id: str, school_id: str
) -> list[StudentParent]:
    stmt = (
        select(StudentParent)
        .join(Parent, StudentParent.parent_id == Parent.id)
        .options(
            selectinload(StudentParent.parent).selectinload(Parent.person),
        )
        .where(
            StudentParent.student_id == student_id,
            Parent.school_id == school_id,
            Parent.deleted_at.is_(None),
        )
    )
    return list((await session.scalars(stmt)).all())


async def create_parent(session: AsyncSession, parent: Parent) -> Parent:
    session.add(parent)
    await session.flush()
    return parent


async def create_student_parent(session: AsyncSession, link: StudentParent) -> StudentParent:
    session.add(link)
    await session.flush()
    return link


async def get_student_parent(
    session: AsyncSession, link_id: str, school_id: str
) -> StudentParent | None:
    stmt = (
        select(StudentParent)
        .join(Parent, StudentParent.parent_id == Parent.id)
        .options(
            selectinload(StudentParent.parent).selectinload(Parent.person),
        )
        .where(
            StudentParent.id == link_id,
            Parent.school_id == school_id,
            Parent.deleted_at.is_(None),
        )
    )
    return (await session.scalars(stmt)).first()


async def get_student_parent_by_pair(
    session: AsyncSession, student_id: str, parent_id: str
) -> StudentParent | None:
    stmt = select(StudentParent).where(
        StudentParent.student_id == student_id,
        StudentParent.parent_id == parent_id,
    )
    return (await session.scalars(stmt)).first()
