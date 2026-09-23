"""Enrollment routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.students.enrollments import repository, service
from app.modules.students.enrollments.permissions import (
    ENROLLMENT_CREATE,
    ENROLLMENT_DELETE,
    ENROLLMENT_LIST,
    ENROLLMENT_READ,
    ENROLLMENT_TRANSFER,
    ENROLLMENT_UPDATE,
)
from app.modules.students.enrollments.schemas import (
    EnrollmentCreate,
    EnrollmentRead,
    EnrollmentTransfer,
    EnrollmentUpdate,
)
from app.modules.students.enums import EnrollmentStatus

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


class EnrollmentDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[EnrollmentRead])
async def list_enrollments(
    student_id: str | None = None,
    academic_year_id: str | None = None,
    cohort_id: str | None = None,
    status: EnrollmentStatus | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(ENROLLMENT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)
    page = await repository.list_enrollments(
        session,
        ctx.school_id,
        params,
        student_id=student_id,
        academic_year_id=academic_year_id,
        cohort_id=cohort_id,
        status=status,
    )
    return CursorPage(
        items=[EnrollmentRead.from_orm_with_relations(e) for e in page.items],
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{enrollment_id}", response_model=EnrollmentRead)
async def get_enrollment(
    enrollment_id: str,
    ctx: RequestContext = Depends(require(ENROLLMENT_READ)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, enrollment_id)
    return EnrollmentRead.from_orm_with_relations(obj)


@router.post("", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    data: EnrollmentCreate,
    ctx: RequestContext = Depends(require(ENROLLMENT_CREATE)),
    session: SessionDep = None,
):
    obj = await service.create(session, ctx, data)
    return EnrollmentRead.from_orm_with_relations(obj)


@router.patch("/{enrollment_id}", response_model=EnrollmentRead)
async def update_enrollment(
    enrollment_id: str,
    data: EnrollmentUpdate,
    ctx: RequestContext = Depends(require(ENROLLMENT_UPDATE)),
    session: SessionDep = None,
):
    obj = await service.update(session, ctx, enrollment_id, data)
    return EnrollmentRead.from_orm_with_relations(obj)


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enrollment(
    enrollment_id: str,
    data: EnrollmentDelete,
    ctx: RequestContext = Depends(require(ENROLLMENT_DELETE)),
    session: SessionDep = None,
):
    await service.delete(session, ctx, enrollment_id, data.version)


@router.post("/{enrollment_id}/transfer", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
async def transfer_enrollment(
    enrollment_id: str,
    data: EnrollmentTransfer,
    ctx: RequestContext = Depends(require(ENROLLMENT_TRANSFER)),
    session: SessionDep = None,
):
    obj = await service.transfer(session, ctx, enrollment_id, data)
    return EnrollmentRead.from_orm_with_relations(obj)
