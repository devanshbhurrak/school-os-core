"""Parent routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.parents import service
from app.modules.parents.enums import ParentStatus
from app.modules.parents.permissions import (
    P_PARENT_CREATE,
    P_PARENT_DELETE,
    P_PARENT_LIST,
    P_PARENT_READ,
    P_PARENT_UPDATE,
    P_STUDENT_PARENT_CREATE,
    P_STUDENT_PARENT_DELETE,
)
from app.modules.parents.schemas import (
    ParentCreate,
    ParentRead,
    ParentUpdate,
    StudentParentCreate,
    StudentParentRead,
)

router = APIRouter(tags=["parents"])

parents_router = APIRouter(prefix="/parents", tags=["parents"])
student_parents_router = APIRouter(tags=["parents"])


class ParentDelete(BaseModel):
    version: int = Field(ge=1)


def _read(parent) -> ParentRead:
    return ParentRead.from_orm_with_person(parent)


def _link_read(link) -> StudentParentRead:
    return StudentParentRead.from_orm_with_parent(link)


@parents_router.post("", response_model=ParentRead, status_code=status.HTTP_201_CREATED)
async def create_parent(
    data: ParentCreate,
    ctx: RequestContext = Depends(require(P_PARENT_CREATE)),
    session: SessionDep = None,
):
    parent = await service.create(session, ctx, data)
    return _read(parent)


@parents_router.get("", response_model=CursorPage[ParentRead])
async def list_parents(
    params: CursorParams = Depends(),
    search: str | None = None,
    status_filter: ParentStatus | None = None,
    ctx: RequestContext = Depends(require(P_PARENT_LIST)),
    session: SessionDep = None,
):
    page = await service.list_parents(session, ctx, params, search=search, status=status_filter)
    page.items = [_read(p) for p in page.items]
    return page


@parents_router.get("/{parent_id}", response_model=ParentRead)
async def get_parent(
    parent_id: str,
    ctx: RequestContext = Depends(require(P_PARENT_READ)),
    session: SessionDep = None,
):
    parent = await service.get(session, ctx, parent_id)
    return _read(parent)


@parents_router.patch("/{parent_id}", response_model=ParentRead)
async def update_parent(
    parent_id: str,
    data: ParentUpdate,
    ctx: RequestContext = Depends(require(P_PARENT_UPDATE)),
    session: SessionDep = None,
):
    parent = await service.get(session, ctx, parent_id)
    updated = await service.update(session, ctx, parent, data)
    return _read(updated)


@parents_router.delete("/{parent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parent(
    parent_id: str,
    data: ParentDelete,
    ctx: RequestContext = Depends(require(P_PARENT_DELETE)),
    session: SessionDep = None,
):
    parent = await service.get(session, ctx, parent_id)
    await service.delete(session, ctx, parent, data.version)


@parents_router.get("/{parent_id}/children", response_model=list[StudentParentRead])
async def list_children(
    parent_id: str,
    ctx: RequestContext = Depends(require(P_PARENT_READ)),
    session: SessionDep = None,
):
    links = await service.list_children(session, ctx, parent_id)
    return [_link_read(link) for link in links]


@student_parents_router.get(
    "/students/{student_id}/parents", response_model=list[StudentParentRead]
)
async def list_parents_for_student(
    student_id: str,
    ctx: RequestContext = Depends(require(P_PARENT_LIST)),
    session: SessionDep = None,
):
    links = await service.list_parents_for_student(session, ctx, student_id)
    return [_link_read(link) for link in links]


@student_parents_router.post(
    "/students/{student_id}/parents",
    response_model=StudentParentRead,
    status_code=status.HTTP_201_CREATED,
)
async def link_parent_to_student(
    student_id: str,
    data: StudentParentCreate,
    ctx: RequestContext = Depends(require(P_STUDENT_PARENT_CREATE)),
    session: SessionDep = None,
):
    link = await service.link_to_student(session, ctx, student_id, data)
    return _link_read(link)


@student_parents_router.delete(
    "/student-parents/{link_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def unlink_parent_from_student(
    link_id: str,
    ctx: RequestContext = Depends(require(P_STUDENT_PARENT_DELETE)),
    session: SessionDep = None,
):
    await service.unlink_from_student(session, ctx, link_id)
