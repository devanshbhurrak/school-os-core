"""Student routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.students import repository, service
from app.modules.students.enums import StudentStatus
from app.modules.students.permissions import (
    P_STUDENT_CREATE,
    P_STUDENT_DELETE,
    P_STUDENT_LIST,
    P_STUDENT_READ,
    P_STUDENT_UPDATE,
)
from app.modules.students.schemas import (
    StudentCreate,
    StudentRead,
    StudentUpdate,
)

router = APIRouter(prefix="/students", tags=["students"])


class StudentDelete(BaseModel):
    version: int = Field(ge=1)


def _read(student) -> StudentRead:
    return StudentRead.from_orm_with_person(student)


@router.get("", response_model=CursorPage[StudentRead])
async def list_students(
    params: CursorParams = Depends(),
    search: str | None = None,
    status: StudentStatus | None = None,
    ctx: RequestContext = Depends(require(P_STUDENT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    page = await repository.list_students(session, ctx.school_id, params, search=search, status=status)
    page.items = [_read(s) for s in page.items]
    return page


@router.get("/{student_id}", response_model=StudentRead)
async def get_student(
    student_id: str,
    ctx: RequestContext = Depends(require(P_STUDENT_READ)),
    session: SessionDep = None,
):
    student = await service.get_owned(session, ctx, student_id)
    return _read(student)


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
async def create_student(
    data: StudentCreate,
    ctx: RequestContext = Depends(require(P_STUDENT_CREATE)),
    session: SessionDep = None,
):
    student = await service.create(session, ctx, data)
    return _read(student)


@router.patch("/{student_id}", response_model=StudentRead)
async def update_student(
    student_id: str,
    data: StudentUpdate,
    ctx: RequestContext = Depends(require(P_STUDENT_UPDATE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, student_id)
    updated = await service.update(session, ctx, obj, data)
    return _read(updated)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str,
    data: StudentDelete,
    ctx: RequestContext = Depends(require(P_STUDENT_DELETE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, student_id)
    await service.delete(session, ctx, obj, data.version)
