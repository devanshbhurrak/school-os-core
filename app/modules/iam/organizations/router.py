"""Organization routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.iam.organizations import repository, service
from app.modules.iam.organizations.permissions import (
    P_ORG_CREATE,
    P_ORG_DELETE,
    P_ORG_LIST,
    P_ORG_READ,
    P_ORG_UPDATE,
)
from app.modules.iam.organizations.schemas import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["iam-organizations"])


class OrganizationDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[OrganizationRead])
async def list_organizations(
    params: CursorParams = Depends(),
    _ctx: RequestContext = Depends(require(P_ORG_LIST)),
    session: SessionDep = None,
):
    page = await repository.list_organizations(session, params)
    return page


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: str,
    _ctx: RequestContext = Depends(require(P_ORG_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, organization_id)


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    ctx: RequestContext = Depends(require(P_ORG_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    organization_id: str,
    data: OrganizationUpdate,
    ctx: RequestContext = Depends(require(P_ORG_UPDATE)),
    session: SessionDep = None,
):
    organization = await service.get_owned(session, organization_id)
    return await service.update(session, ctx, organization, data)


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: str,
    data: OrganizationDelete,
    ctx: RequestContext = Depends(require(P_ORG_DELETE)),
    session: SessionDep = None,
):
    organization = await service.get_owned(session, organization_id)
    await service.delete(session, ctx, organization, data.version)
