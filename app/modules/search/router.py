"""Global search across students and teachers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import require_authenticated
from app.core.context import RequestContext
from app.db.rls import set_tenant_context
from app.db.session import SessionDep
from app.modules.people.models import Person
from app.modules.students.models import Student
from app.modules.teachers.models import Teacher

router = APIRouter(tags=["Search"])


@router.get("/search")
async def global_search(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, le=50),
    session: SessionDep = None,
    ctx: RequestContext = Depends(require_authenticated),
):
    """Search across students and teachers by name or ID number."""
    if not ctx.school_id:
        return {"students": [], "teachers": []}

    await set_tenant_context(
        session,
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
    )

    search_term = f"%{q}%"
    q_lower = q.lower()

    # Search students — join Person for name fields
    students_stmt = (
        select(Student, Person)
        .join(Person, Student.person_id == Person.id)
        .where(
            Student.school_id == ctx.school_id,
            Student.deleted_at.is_(None),
            or_(
                func.lower(
                    func.coalesce(Person.first_name, "")
                    + " "
                    + func.coalesce(Person.last_name, "")
                ).contains(q_lower),
                Student.admission_number.ilike(search_term),
            ),
        )
        .limit(limit)
    )

    students_result = await session.execute(students_stmt)
    students_rows = students_result.all()

    # Search teachers — join Person for name fields
    teachers_stmt = (
        select(Teacher, Person)
        .join(Person, Teacher.person_id == Person.id)
        .where(
            Teacher.school_id == ctx.school_id,
            Teacher.deleted_at.is_(None),
            or_(
                func.lower(
                    func.coalesce(Person.first_name, "")
                    + " "
                    + func.coalesce(Person.last_name, "")
                ).contains(q_lower),
                Teacher.employee_number.ilike(search_term),
            ),
        )
        .limit(limit)
    )

    teachers_result = await session.execute(teachers_stmt)
    teachers_rows = teachers_result.all()

    def _student_item(student: Student, person: Person) -> dict:
        return {
            "id": student.id,
            "admission_number": student.admission_number,
            "status": student.status,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "person_id": person.id,
        }

    def _teacher_item(teacher: Teacher, person: Person) -> dict:
        return {
            "id": teacher.id,
            "employee_number": teacher.employee_number,
            "designation": teacher.designation,
            "status": teacher.status,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "person_id": person.id,
        }

    return {
        "students": [_student_item(s, p) for s, p in students_rows],
        "teachers": [_teacher_item(t, p) for t, p in teachers_rows],
    }
