"""Cohort routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.academic.cohorts import repository, service
from app.modules.academic.cohorts.permissions import (
    P_COHORT_CREATE,
    P_COHORT_DELETE,
    P_COHORT_LIST,
    P_COHORT_READ,
    P_COHORT_UPDATE,
)
from app.modules.academic.cohorts.schemas import (
    CohortCreate,
    CohortRead,
    CohortUpdate,
)

router = APIRouter(prefix="/cohorts", tags=["academic-cohorts"])


class CohortDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[CohortRead])
async def list_cohorts(
    academic_year_id: str | None = None,
    academic_class_id: str | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_COHORT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage as CP
        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_cohorts(
        session, ctx.school_id, params,
        academic_year_id=academic_year_id,
        academic_class_id=academic_class_id,
    )


@router.get("/{cohort_id}", response_model=CohortRead)
async def get_cohort(
    cohort_id: str,
    ctx: RequestContext = Depends(require(P_COHORT_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, cohort_id)


@router.post("", response_model=CohortRead, status_code=status.HTTP_201_CREATED)
async def create_cohort(
    data: CohortCreate,
    ctx: RequestContext = Depends(require(P_COHORT_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{cohort_id}", response_model=CohortRead)
async def update_cohort(
    cohort_id: str,
    data: CohortUpdate,
    ctx: RequestContext = Depends(require(P_COHORT_UPDATE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, cohort_id)
    return await service.update(session, ctx, obj, data)


@router.delete("/{cohort_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cohort(
    cohort_id: str,
    data: CohortDelete,
    ctx: RequestContext = Depends(require(P_COHORT_DELETE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, cohort_id)
    await service.delete(session, ctx, obj, data.version)
