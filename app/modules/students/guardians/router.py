"""Guardian routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.authz import require
from app.core.context import RequestContext
from app.db.session import SessionDep
from app.modules.students.guardians import repository, service
from app.modules.students.guardians.permissions import (
    GUARDIAN_CREATE,
    GUARDIAN_DELETE,
    GUARDIAN_LIST,
    GUARDIAN_READ,
    GUARDIAN_UPDATE,
)
from app.modules.students.guardians.schemas import (
    GuardianCreate,
    GuardianRead,
    GuardianUpdate,
)

students_router = APIRouter(prefix="/students", tags=["guardians"])
guardians_router = APIRouter(prefix="/student-guardians", tags=["guardians"])


def _read(guardian) -> GuardianRead:
    return GuardianRead.from_orm_with_person(guardian)


@students_router.get("/{student_id}/guardians", response_model=list[GuardianRead])
async def list_guardians(
    student_id: str,
    ctx: RequestContext = Depends(require(GUARDIAN_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        return []
    guardians = await repository.list_for_student(session, student_id, ctx.school_id)
    return [_read(g) for g in guardians]


@guardians_router.get("/{id}", response_model=GuardianRead)
async def get_guardian(
    id: str,
    ctx: RequestContext = Depends(require(GUARDIAN_READ)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.errors import NotFoundError
        raise NotFoundError("The guardian link was not found.", code="GUARDIAN_NOT_FOUND")
    guardian = await repository.get_by_id(session, id, ctx.school_id)
    if guardian is None:
        from app.core.errors import NotFoundError
        raise NotFoundError("The guardian link was not found.", code="GUARDIAN_NOT_FOUND")
    return _read(guardian)


@guardians_router.post("", response_model=GuardianRead, status_code=status.HTTP_201_CREATED)
async def add_guardian(
    data: GuardianCreate,
    ctx: RequestContext = Depends(require(GUARDIAN_CREATE)),
    session: SessionDep = None,
):
    guardian = await service.add_guardian(session, ctx, data)
    return _read(guardian)


@guardians_router.patch("/{id}", response_model=GuardianRead)
async def update_guardian(
    id: str,
    data: GuardianUpdate,
    ctx: RequestContext = Depends(require(GUARDIAN_UPDATE)),
    session: SessionDep = None,
):
    guardian = await service.update_guardian(session, ctx, id, data)
    return _read(guardian)


@guardians_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_guardian(
    id: str,
    ctx: RequestContext = Depends(require(GUARDIAN_DELETE)),
    session: SessionDep = None,
):
    await service.remove_guardian(session, ctx, id)
