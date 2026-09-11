"""Role routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.iam.roles import repository, service
from app.modules.iam.roles.permissions import (
    P_ROLE_CREATE,
    P_ROLE_DELETE,
    P_ROLE_LIST,
    P_ROLE_READ,
    P_ROLE_UPDATE,
)
from app.modules.iam.roles.schemas import RoleCreate, RoleRead, RoleUpdate

router = APIRouter(prefix="/roles", tags=["iam-roles"])


class RoleDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[RoleRead])
async def list_roles(
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_ROLE_LIST)),
    session: SessionDep = None,
):
    if ctx.organization_id is None:
        from app.core.pagination import CursorPage as CP

        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_roles(session, ctx.organization_id, params)


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: str,
    ctx: RequestContext = Depends(require(P_ROLE_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, role_id)


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    ctx: RequestContext = Depends(require(P_ROLE_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: str,
    data: RoleUpdate,
    ctx: RequestContext = Depends(require(P_ROLE_UPDATE)),
    session: SessionDep = None,
):
    role = await service.get_owned(session, ctx, role_id)
    return await service.update(session, ctx, role, data)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    data: RoleDelete,
    ctx: RequestContext = Depends(require(P_ROLE_DELETE)),
    session: SessionDep = None,
):
    role = await service.get_owned(session, ctx, role_id)
    await service.delete(session, ctx, role, data.version)
