"""AcademicTerm routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.academic.academic_terms import repository, service
from app.modules.academic.academic_terms.permissions import (
    P_ACADEMIC_TERM_CREATE,
    P_ACADEMIC_TERM_DELETE,
    P_ACADEMIC_TERM_LIST,
    P_ACADEMIC_TERM_READ,
    P_ACADEMIC_TERM_UPDATE,
)
from app.modules.academic.academic_terms.schemas import (
    AcademicTermCreate,
    AcademicTermRead,
    AcademicTermUpdate,
)

router = APIRouter(prefix="/academic-terms", tags=["academic-terms"])


class AcademicTermDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[AcademicTermRead])
async def list_academic_terms(
    academic_year_id: str | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_ACADEMIC_TERM_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_academic_terms(session, ctx.school_id, params, academic_year_id=academic_year_id)


@router.get("/{term_id}", response_model=AcademicTermRead)
async def get_academic_term(
    term_id: str,
    ctx: RequestContext = Depends(require(P_ACADEMIC_TERM_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, term_id)


@router.post("", response_model=AcademicTermRead, status_code=status.HTTP_201_CREATED)
async def create_academic_term(
    data: AcademicTermCreate,
    ctx: RequestContext = Depends(require(P_ACADEMIC_TERM_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{term_id}", response_model=AcademicTermRead)
async def update_academic_term(
    term_id: str,
    data: AcademicTermUpdate,
    ctx: RequestContext = Depends(require(P_ACADEMIC_TERM_UPDATE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, term_id)
    return await service.update(session, ctx, obj, data)


@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_academic_term(
    term_id: str,
    data: AcademicTermDelete,
    ctx: RequestContext = Depends(require(P_ACADEMIC_TERM_DELETE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, term_id)
    await service.delete(session, ctx, obj, data.version)
