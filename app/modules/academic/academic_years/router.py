"""AcademicYear routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.academic.academic_years import repository, service
from app.modules.academic.academic_years.permissions import (
    P_ACADEMIC_YEAR_CREATE,
    P_ACADEMIC_YEAR_DELETE,
    P_ACADEMIC_YEAR_LIST,
    P_ACADEMIC_YEAR_READ,
    P_ACADEMIC_YEAR_UPDATE,
)
from app.modules.academic.academic_years.schemas import (
    AcademicYearCreate,
    AcademicYearRead,
    AcademicYearUpdate,
)

router = APIRouter(prefix="/academic-years", tags=["academic-years"])


class AcademicYearDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[AcademicYearRead])
async def list_academic_years(
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_ACADEMIC_YEAR_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_academic_years(session, ctx.school_id, params)


@router.get("/{year_id}", response_model=AcademicYearRead)
async def get_academic_year(
    year_id: str,
    ctx: RequestContext = Depends(require(P_ACADEMIC_YEAR_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, year_id)


@router.post("", response_model=AcademicYearRead, status_code=status.HTTP_201_CREATED)
async def create_academic_year(
    data: AcademicYearCreate,
    ctx: RequestContext = Depends(require(P_ACADEMIC_YEAR_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{year_id}", response_model=AcademicYearRead)
async def update_academic_year(
    year_id: str,
    data: AcademicYearUpdate,
    ctx: RequestContext = Depends(require(P_ACADEMIC_YEAR_UPDATE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, year_id)
    return await service.update(session, ctx, obj, data)


@router.delete("/{year_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_academic_year(
    year_id: str,
    data: AcademicYearDelete,
    ctx: RequestContext = Depends(require(P_ACADEMIC_YEAR_DELETE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, year_id)
    await service.delete(session, ctx, obj, data.version)
