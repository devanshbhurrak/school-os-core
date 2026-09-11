"""Person routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.people.persons import repository, service
from app.modules.people.persons.permissions import (
    P_PERSON_CREATE,
    P_PERSON_DELETE,
    P_PERSON_LIST,
    P_PERSON_MERGE,
    P_PERSON_READ,
    P_PERSON_UPDATE,
)
from app.modules.people.persons.schemas import (
    PersonCreate,
    PersonMerge,
    PersonRead,
    PersonUpdate,
)

router = APIRouter(prefix="/persons", tags=["people-persons"])


class PersonDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[PersonRead])
async def list_persons(
    search: str | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_PERSON_LIST)),
    session: SessionDep = None,
):
    if ctx.organization_id is None:
        from app.core.pagination import CursorPage as CP

        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_persons(session, ctx.organization_id, params, search=search)


@router.get("/{person_id}", response_model=PersonRead)
async def get_person(
    person_id: str,
    ctx: RequestContext = Depends(require(P_PERSON_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, person_id)


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
async def create_person(
    data: PersonCreate,
    ctx: RequestContext = Depends(require(P_PERSON_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{person_id}", response_model=PersonRead)
async def update_person(
    person_id: str,
    data: PersonUpdate,
    ctx: RequestContext = Depends(require(P_PERSON_UPDATE)),
    session: SessionDep = None,
):
    person = await service.get_owned(session, ctx, person_id)
    return await service.update(session, ctx, person, data)


@router.post("/{person_id}/merge", response_model=PersonRead)
async def merge_person(
    person_id: str,
    data: PersonMerge,
    ctx: RequestContext = Depends(require(P_PERSON_MERGE)),
    session: SessionDep = None,
):
    person = await service.get_owned(session, ctx, person_id)
    return await service.merge(session, ctx, person, data)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: str,
    data: PersonDelete,
    ctx: RequestContext = Depends(require(P_PERSON_DELETE)),
    session: SessionDep = None,
):
    person = await service.get_owned(session, ctx, person_id)
    await service.delete(session, ctx, person, data.version)
