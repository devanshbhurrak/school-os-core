"""Address routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.people.addresses import repository, service
from app.modules.people.addresses.permissions import (
    P_ADDRESS_CREATE,
    P_ADDRESS_DELETE,
    P_ADDRESS_LIST,
    P_ADDRESS_READ,
    P_ADDRESS_UPDATE,
)
from app.modules.people.addresses.schemas import (
    AddressCreate,
    AddressRead,
    AddressUpdate,
)

router = APIRouter(prefix="/addresses", tags=["people-addresses"])


class AddressDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[AddressRead])
async def list_addresses(
    entity_type: str,
    entity_id: str,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_ADDRESS_LIST)),
    session: SessionDep = None,
):
    if ctx.organization_id is None:
        from app.core.pagination import CursorPage as CP

        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_for_entity(session, ctx.organization_id, entity_type, entity_id, params)


@router.get("/{address_id}", response_model=AddressRead)
async def get_address(
    address_id: str,
    ctx: RequestContext = Depends(require(P_ADDRESS_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, address_id)


@router.post("", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
async def create_address(
    data: AddressCreate,
    ctx: RequestContext = Depends(require(P_ADDRESS_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{address_id}", response_model=AddressRead)
async def update_address(
    address_id: str,
    data: AddressUpdate,
    ctx: RequestContext = Depends(require(P_ADDRESS_UPDATE)),
    session: SessionDep = None,
):
    address = await service.get_owned(session, ctx, address_id)
    return await service.update(session, ctx, address, data)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: str,
    data: AddressDelete,
    ctx: RequestContext = Depends(require(P_ADDRESS_DELETE)),
    session: SessionDep = None,
):
    address = await service.get_owned(session, ctx, address_id)
    await service.delete(session, ctx, address, data.version)
