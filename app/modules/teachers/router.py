"""Teacher and TeacherAssignment routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.teachers import repository, service
from app.modules.teachers.models import Teacher, TeacherAssignment
from app.modules.teachers.permissions import (
    P_ASSIGNMENT_CREATE,
    P_ASSIGNMENT_DELETE,
    P_ASSIGNMENT_LIST,
    P_ASSIGNMENT_READ,
    P_ASSIGNMENT_UPDATE,
    P_TEACHER_CREATE,
    P_TEACHER_DELETE,
    P_TEACHER_LIST,
    P_TEACHER_READ,
    P_TEACHER_UPDATE,
)
from app.modules.teachers.schemas import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentUpdate,
    TeacherCreate,
    TeacherRead,
    TeacherUpdate,
)

router = APIRouter(tags=["teachers"])


# ---------------------------------------------------------------------------
# Helpers to build response objects with joined display fields
# ---------------------------------------------------------------------------

async def _teacher_read(teacher: Teacher) -> TeacherRead:
    """Build a TeacherRead by pulling display fields from the loaded person."""
    data = {
        "id": teacher.id,
        "school_id": teacher.school_id,
        "organization_id": teacher.organization_id,
        "person_id": teacher.person_id,
        "employee_number": teacher.employee_number,
        "designation": teacher.designation,
        "joining_date": teacher.joining_date,
        "leaving_date": teacher.leaving_date,
        "status": teacher.status,
        "person_first_name": teacher.person.first_name,
        "person_last_name": teacher.person.last_name,
        "person_primary_email": teacher.person.primary_email,
        "version": teacher.version,
        "created_at": teacher.created_at,
        "updated_at": teacher.updated_at,
    }
    return TeacherRead.model_validate(data)


async def _assignment_read(session, assignment: TeacherAssignment) -> AssignmentRead:
    """Build an AssignmentRead by loading joined display fields."""
    joined = await repository.load_assignment_joined(session, assignment)
    teacher = joined["teacher"]
    cohort = joined["cohort"]
    subj = joined["subject"]
    year = joined["year"]

    data = {
        "id": assignment.id,
        "school_id": assignment.school_id,
        "organization_id": assignment.organization_id,
        "teacher_id": assignment.teacher_id,
        "cohort_id": assignment.cohort_id,
        "subject_id": assignment.subject_id,
        "academic_year_id": assignment.academic_year_id,
        "role": assignment.role,
        "start_date": assignment.start_date,
        "end_date": assignment.end_date,
        "status": assignment.status,
        "teacher_person_first_name": teacher.person.first_name if teacher else "",
        "teacher_person_last_name": teacher.person.last_name if teacher else None,
        "cohort_name": cohort.name if cohort else "",
        "subject_name": subj.name if subj else None,
        "academic_year_code": year.code if year else "",
        "version": assignment.version,
        "created_at": assignment.created_at,
    }
    return AssignmentRead.model_validate(data)


# ---------------------------------------------------------------------------
# Teachers
# ---------------------------------------------------------------------------

class TeacherDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("/teachers", response_model=CursorPage[TeacherRead])
async def list_teachers(
    params: CursorParams = Depends(),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    ctx: RequestContext = Depends(require(P_TEACHER_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)
    page = await repository.list_teachers(session, ctx.school_id, params, search=search, status=status)
    # For list we need to load person for each teacher via selectinload
    teachers_with_persons = []
    for teacher in page.items:
        # Reload with person if not loaded
        loaded = await repository.get_by_id(session, ctx.school_id, teacher.id)
        if loaded:
            teachers_with_persons.append(await _teacher_read(loaded))
    return CursorPage(items=teachers_with_persons, next_cursor=page.next_cursor, has_more=page.has_more)


@router.get("/teachers/{teacher_id}", response_model=TeacherRead)
async def get_teacher(
    teacher_id: str,
    ctx: RequestContext = Depends(require(P_TEACHER_READ)),
    session: SessionDep = None,
):
    teacher = await service.get_owned(session, ctx, teacher_id)
    return await _teacher_read(teacher)


@router.post("/teachers", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    data: TeacherCreate,
    ctx: RequestContext = Depends(require(P_TEACHER_CREATE)),
    session: SessionDep = None,
):
    teacher = await service.create(session, ctx, data)
    return await _teacher_read(teacher)


@router.patch("/teachers/{teacher_id}", response_model=TeacherRead)
async def update_teacher(
    teacher_id: str,
    data: TeacherUpdate,
    ctx: RequestContext = Depends(require(P_TEACHER_UPDATE)),
    session: SessionDep = None,
):
    teacher = await service.get_owned(session, ctx, teacher_id)
    updated = await service.update(session, ctx, teacher, data)
    return await _teacher_read(updated)


@router.delete("/teachers/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_teacher(
    teacher_id: str,
    data: TeacherDelete,
    ctx: RequestContext = Depends(require(P_TEACHER_DELETE)),
    session: SessionDep = None,
):
    teacher = await service.get_owned(session, ctx, teacher_id)
    await service.delete(session, ctx, teacher, data.version)


# ---------------------------------------------------------------------------
# Teacher Assignments
# ---------------------------------------------------------------------------

class AssignmentEnd(BaseModel):
    version: int = Field(ge=1)


@router.get("/teacher-assignments", response_model=CursorPage[AssignmentRead])
async def list_assignments(
    params: CursorParams = Depends(),
    teacher_id: str | None = Query(default=None),
    cohort_id: str | None = Query(default=None),
    academic_year_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    ctx: RequestContext = Depends(require(P_ASSIGNMENT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)
    page = await repository.list_assignments(
        session, ctx.school_id, params,
        teacher_id=teacher_id,
        cohort_id=cohort_id,
        academic_year_id=academic_year_id,
        status=status,
    )
    items = [await _assignment_read(session, a) for a in page.items]
    return CursorPage(items=items, next_cursor=page.next_cursor, has_more=page.has_more)


@router.get("/teacher-assignments/{assignment_id}", response_model=AssignmentRead)
async def get_assignment(
    assignment_id: str,
    ctx: RequestContext = Depends(require(P_ASSIGNMENT_READ)),
    session: SessionDep = None,
):
    assignment = await service.get_assignment_owned(session, ctx, assignment_id)
    return await _assignment_read(session, assignment)


@router.post("/teacher-assignments", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    data: AssignmentCreate,
    ctx: RequestContext = Depends(require(P_ASSIGNMENT_CREATE)),
    session: SessionDep = None,
):
    assignment = await service.create_assignment(session, ctx, data)
    return await _assignment_read(session, assignment)


@router.patch("/teacher-assignments/{assignment_id}", response_model=AssignmentRead)
async def update_assignment(
    assignment_id: str,
    data: AssignmentUpdate,
    ctx: RequestContext = Depends(require(P_ASSIGNMENT_UPDATE)),
    session: SessionDep = None,
):
    assignment = await service.get_assignment_owned(session, ctx, assignment_id)
    updated = await service.update_assignment(session, ctx, assignment, data)
    return await _assignment_read(session, updated)


@router.delete("/teacher-assignments/{assignment_id}", response_model=AssignmentRead)
async def end_assignment(
    assignment_id: str,
    data: AssignmentEnd,
    ctx: RequestContext = Depends(require(P_ASSIGNMENT_DELETE)),
    session: SessionDep = None,
):
    assignment = await service.get_assignment_owned(session, ctx, assignment_id)
    ended = await service.end_assignment(session, ctx, assignment, data.version)
    return await _assignment_read(session, ended)
