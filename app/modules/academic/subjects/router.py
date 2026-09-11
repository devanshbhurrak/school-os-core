"""Subject routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.academic.subjects import repository, service
from app.modules.academic.subjects.permissions import (
    P_SUBJECT_CREATE,
    P_SUBJECT_DELETE,
    P_SUBJECT_LIST,
    P_SUBJECT_READ,
    P_SUBJECT_UPDATE,
)
from app.modules.academic.subjects.schemas import (
    SubjectCreate,
    SubjectRead,
    SubjectUpdate,
)

router = APIRouter(prefix="/subjects", tags=["academic-subjects"])


class SubjectDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[SubjectRead])
async def list_subjects(
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_SUBJECT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_subjects(session, ctx.school_id, params)


@router.get("/{subject_id}", response_model=SubjectRead)
async def get_subject(
    subject_id: str,
    ctx: RequestContext = Depends(require(P_SUBJECT_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, subject_id)


@router.post("", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    ctx: RequestContext = Depends(require(P_SUBJECT_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{subject_id}", response_model=SubjectRead)
async def update_subject(
    subject_id: str,
    data: SubjectUpdate,
    ctx: RequestContext = Depends(require(P_SUBJECT_UPDATE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, subject_id)
    return await service.update(session, ctx, obj, data)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: str,
    data: SubjectDelete,
    ctx: RequestContext = Depends(require(P_SUBJECT_DELETE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, subject_id)
    await service.delete(session, ctx, obj, data.version)
