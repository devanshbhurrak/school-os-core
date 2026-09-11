"""ClassSubject routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.academic.class_subjects import repository, service
from app.modules.academic.class_subjects.permissions import (
    P_CLASS_SUBJECT_CREATE,
    P_CLASS_SUBJECT_DELETE,
    P_CLASS_SUBJECT_LIST,
    P_CLASS_SUBJECT_READ,
)
from app.modules.academic.class_subjects.schemas import (
    ClassSubjectCreate,
    ClassSubjectRead,
)

router = APIRouter(prefix="/class-subjects", tags=["academic-class-subjects"])


@router.get("", response_model=CursorPage[ClassSubjectRead])
async def list_class_subjects(
    academic_class_id: str | None = None,
    year_id: str | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_CLASS_SUBJECT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_class_subjects(
        session, ctx.school_id, params,
        academic_class_id=academic_class_id,
        year_id=year_id,
    )


@router.get("/{class_subject_id}", response_model=ClassSubjectRead)
async def get_class_subject(
    class_subject_id: str,
    ctx: RequestContext = Depends(require(P_CLASS_SUBJECT_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, class_subject_id)


@router.post("", response_model=ClassSubjectRead, status_code=status.HTTP_201_CREATED)
async def create_class_subject(
    data: ClassSubjectCreate,
    ctx: RequestContext = Depends(require(P_CLASS_SUBJECT_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.delete("/{class_subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class_subject(
    class_subject_id: str,
    ctx: RequestContext = Depends(require(P_CLASS_SUBJECT_DELETE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, class_subject_id)
    await service.delete(session, ctx, obj)
