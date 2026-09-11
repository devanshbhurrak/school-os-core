"""Membership routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.iam.memberships import repository, service
from app.modules.iam.memberships.permissions import (
    P_MEMBERSHIP_CREATE,
    P_MEMBERSHIP_DELETE,
    P_MEMBERSHIP_GRANT_ROLE,
    P_MEMBERSHIP_LIST,
    P_MEMBERSHIP_READ,
    P_MEMBERSHIP_REVOKE_ROLE,
    P_MEMBERSHIP_UPDATE,
)
from app.modules.iam.memberships.schemas import (
    MembershipCreate,
    MembershipRead,
    MembershipUpdate,
    RoleGrantCreate,
)

router = APIRouter(prefix="/memberships", tags=["iam-memberships"])


class MembershipDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[MembershipRead])
async def list_memberships(
    school_id: str | None = None,
    user_id: str | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_MEMBERSHIP_LIST)),
    session: SessionDep = None,
):
    if ctx.organization_id is None:
        from app.core.pagination import CursorPage as CP

        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_memberships(
        session, ctx.organization_id, params, school_id=school_id, user_id=user_id
    )


@router.get("/{membership_id}", response_model=MembershipRead)
async def get_membership(
    membership_id: str,
    ctx: RequestContext = Depends(require(P_MEMBERSHIP_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, membership_id)


@router.post("", response_model=MembershipRead, status_code=status.HTTP_201_CREATED)
async def create_membership(
    data: MembershipCreate,
    ctx: RequestContext = Depends(require(P_MEMBERSHIP_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{membership_id}", response_model=MembershipRead)
async def update_membership(
    membership_id: str,
    data: MembershipUpdate,
    ctx: RequestContext = Depends(require(P_MEMBERSHIP_UPDATE)),
    session: SessionDep = None,
):
    membership = await service.get_owned(session, ctx, membership_id)
    return await service.update(session, ctx, membership, data)


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_membership(
    membership_id: str,
    data: MembershipDelete,
    ctx: RequestContext = Depends(require(P_MEMBERSHIP_DELETE)),
    session: SessionDep = None,
):
    membership = await service.get_owned(session, ctx, membership_id)
    await service.end(session, ctx, membership, data.version)


@router.post("/{membership_id}/roles", response_model=MembershipRead, status_code=status.HTTP_201_CREATED)
async def grant_role(
    membership_id: str,
    data: RoleGrantCreate,
    ctx: RequestContext = Depends(require(P_MEMBERSHIP_GRANT_ROLE)),
    session: SessionDep = None,
):
    membership = await service.get_owned(session, ctx, membership_id)
    await service.grant_role(session, ctx, membership, data)
    membership = await service.get_owned(session, ctx, membership_id)
    return membership


@router.delete("/{membership_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_role(
    membership_id: str,
    role_id: str,
    ctx: RequestContext = Depends(require(P_MEMBERSHIP_REVOKE_ROLE)),
    session: SessionDep = None,
):
    membership = await service.get_owned(session, ctx, membership_id)
    await service.revoke_role(session, ctx, membership, role_id)
