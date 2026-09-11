"""Contact routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.people.contacts import repository, service
from app.modules.people.contacts.permissions import (
    P_CONTACT_CREATE,
    P_CONTACT_DELETE,
    P_CONTACT_LIST,
    P_CONTACT_READ,
    P_CONTACT_UPDATE,
)
from app.modules.people.contacts.schemas import (
    ContactCreate,
    ContactRead,
    ContactUpdate,
)

router = APIRouter(prefix="/contacts", tags=["people-contacts"])


@router.get("", response_model=CursorPage[ContactRead])
async def list_contacts(
    entity_type: str,
    entity_id: str,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_CONTACT_LIST)),
    session: SessionDep = None,
):
    if ctx.organization_id is None:
        from app.core.pagination import CursorPage as CP

        return CP(items=[], next_cursor=None, has_more=False)
    return await repository.list_for_entity(session, ctx.organization_id, entity_type, entity_id, params)


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: str,
    ctx: RequestContext = Depends(require(P_CONTACT_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, contact_id)


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    ctx: RequestContext = Depends(require(P_CONTACT_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    ctx: RequestContext = Depends(require(P_CONTACT_UPDATE)),
    session: SessionDep = None,
):
    contact = await service.get_owned(session, ctx, contact_id)
    return await service.update(session, ctx, contact, data)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: str,
    ctx: RequestContext = Depends(require(P_CONTACT_DELETE)),
    session: SessionDep = None,
):
    contact = await service.get_owned(session, ctx, contact_id)
    await service.delete(session, ctx, contact)
