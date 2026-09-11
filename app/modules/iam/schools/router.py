"""School routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.iam.schools import repository, service
from app.modules.iam.schools.permissions import (
    P_SCHOOL_CREATE,
    P_SCHOOL_DELETE,
    P_SCHOOL_LIST,
    P_SCHOOL_READ,
    P_SCHOOL_UPDATE,
)
from app.modules.iam.schools.schemas import (
    SchoolCreate,
    SchoolRead,
    SchoolUpdate,
)

router = APIRouter(prefix="/schools", tags=["iam-schools"])


class SchoolDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[SchoolRead])
async def list_schools(
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_SCHOOL_LIST)),
    session: SessionDep = None,
):
    if ctx.organization_id is None:
        from app.core.pagination import CursorPage as CP

        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_schools(session, ctx.organization_id, params)


@router.get("/{school_id}", response_model=SchoolRead)
async def get_school(
    school_id: str,
    ctx: RequestContext = Depends(require(P_SCHOOL_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, school_id)


@router.post("", response_model=SchoolRead, status_code=status.HTTP_201_CREATED)
async def create_school(
    data: SchoolCreate,
    ctx: RequestContext = Depends(require(P_SCHOOL_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{school_id}", response_model=SchoolRead)
async def update_school(
    school_id: str,
    data: SchoolUpdate,
    ctx: RequestContext = Depends(require(P_SCHOOL_UPDATE)),
    session: SessionDep = None,
):
    school = await service.get_owned(session, ctx, school_id)
    return await service.update(session, ctx, school, data)


@router.delete("/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_school(
    school_id: str,
    data: SchoolDelete,
    ctx: RequestContext = Depends(require(P_SCHOOL_DELETE)),
    session: SessionDep = None,
):
    school = await service.get_owned(session, ctx, school_id)
    await service.delete(session, ctx, school, data.version)
