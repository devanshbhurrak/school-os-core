"""User routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.iam.users import repository, service
from app.modules.iam.users.permissions import (
    P_USER_CREATE,
    P_USER_DELETE,
    P_USER_LIST,
    P_USER_READ,
    P_USER_UPDATE,
)
from app.modules.iam.users.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["iam-users"])


class UserDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[UserRead])
async def list_users(
    search: str | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_USER_LIST)),
    session: SessionDep = None,
):
    if ctx.is_platform_admin:
        return await repository.list_all_users(session, params, search=search)
    if ctx.organization_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)
    return await repository.list_users_in_org(session, ctx.organization_id, params, search=search)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str,
    ctx: RequestContext = Depends(require(P_USER_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, user_id)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    ctx: RequestContext = Depends(require(P_USER_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: str,
    data: UserUpdate,
    ctx: RequestContext = Depends(require(P_USER_UPDATE)),
    session: SessionDep = None,
):
    user = await service.get_owned(session, ctx, user_id)
    return await service.update(session, ctx, user, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    data: UserDelete,
    ctx: RequestContext = Depends(require(P_USER_DELETE)),
    session: SessionDep = None,
):
    user = await service.get_owned(session, ctx, user_id)
    await service.delete(session, ctx, user, data.version)
