"""AcademicClass routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.academic.academic_classes import repository, service
from app.modules.academic.academic_classes.permissions import (
    P_ACADEMIC_CLASS_CREATE,
    P_ACADEMIC_CLASS_DELETE,
    P_ACADEMIC_CLASS_LIST,
    P_ACADEMIC_CLASS_READ,
    P_ACADEMIC_CLASS_UPDATE,
)
from app.modules.academic.academic_classes.schemas import (
    AcademicClassCreate,
    AcademicClassRead,
    AcademicClassUpdate,
)

router = APIRouter(prefix="/academic-classes", tags=["academic-classes"])


class AcademicClassDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[AcademicClassRead])
async def list_academic_classes(
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_ACADEMIC_CLASS_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_academic_classes(session, ctx.school_id, params)


@router.get("/{academic_class_id}", response_model=AcademicClassRead)
async def get_academic_class(
    academic_class_id: str,
    ctx: RequestContext = Depends(require(P_ACADEMIC_CLASS_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, academic_class_id)


@router.post("", response_model=AcademicClassRead, status_code=status.HTTP_201_CREATED)
async def create_academic_class(
    data: AcademicClassCreate,
    ctx: RequestContext = Depends(require(P_ACADEMIC_CLASS_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{academic_class_id}", response_model=AcademicClassRead)
async def update_academic_class(
    academic_class_id: str,
    data: AcademicClassUpdate,
    ctx: RequestContext = Depends(require(P_ACADEMIC_CLASS_UPDATE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, academic_class_id)
    return await service.update(session, ctx, obj, data)


@router.delete("/{academic_class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_academic_class(
    academic_class_id: str,
    data: AcademicClassDelete,
    ctx: RequestContext = Depends(require(P_ACADEMIC_CLASS_DELETE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, academic_class_id)
    await service.delete(session, ctx, obj, data.version)
