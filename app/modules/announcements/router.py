"""Announcement routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.announcements import repository, service
from app.modules.announcements.enums import AnnouncementPriority, AnnouncementStatus
from app.modules.announcements.permissions import (
    P_ANNOUNCEMENT_ARCHIVE,
    P_ANNOUNCEMENT_CREATE,
    P_ANNOUNCEMENT_DELETE,
    P_ANNOUNCEMENT_LIST,
    P_ANNOUNCEMENT_PUBLISH,
    P_ANNOUNCEMENT_READ,
    P_ANNOUNCEMENT_UPDATE,
)
from app.modules.announcements.schemas import (
    AnnouncementCreate,
    AnnouncementFeedItem,
    AnnouncementPublish,
    AnnouncementRead,
    AnnouncementUpdate,
)

router = APIRouter(prefix="/announcements", tags=["announcements"])


class AnnouncementArchive(BaseModel):
    version: int = Field(ge=1)


class AnnouncementDelete(BaseModel):
    version: int = Field(ge=1)


@router.get("", response_model=CursorPage[AnnouncementRead])
async def list_announcements(
    params: CursorParams = Depends(),
    status: AnnouncementStatus | None = None,
    priority: AnnouncementPriority | None = None,
    ctx: RequestContext = Depends(require(P_ANNOUNCEMENT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)
    return await repository.list_announcements(session, ctx.school_id, params, status=status, priority=priority)


@router.get("/feed", response_model=CursorPage[AnnouncementFeedItem])
async def list_announcement_feed(
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_ANNOUNCEMENT_LIST)),
    session: SessionDep = None,
):
    if ctx.school_id is None:
        return CursorPage(items=[], next_cursor=None, has_more=False)
    return await repository.list_feed(session, ctx.school_id, params)


@router.get("/{announcement_id}", response_model=AnnouncementRead)
async def get_announcement(
    announcement_id: str,
    ctx: RequestContext = Depends(require(P_ANNOUNCEMENT_READ)),
    session: SessionDep = None,
):
    return await service.get_owned(session, ctx, announcement_id)


@router.post("", response_model=AnnouncementRead, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    data: AnnouncementCreate,
    ctx: RequestContext = Depends(require(P_ANNOUNCEMENT_CREATE)),
    session: SessionDep = None,
):
    return await service.create(session, ctx, data)


@router.patch("/{announcement_id}", response_model=AnnouncementRead)
async def update_announcement(
    announcement_id: str,
    data: AnnouncementUpdate,
    ctx: RequestContext = Depends(require(P_ANNOUNCEMENT_UPDATE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, announcement_id)
    return await service.update(session, ctx, obj, data)


@router.post("/{announcement_id}/publish", response_model=AnnouncementRead)
async def publish_announcement(
    announcement_id: str,
    data: AnnouncementPublish,
    ctx: RequestContext = Depends(require(P_ANNOUNCEMENT_PUBLISH)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, announcement_id)
    return await service.publish(session, ctx, obj, data)


@router.post("/{announcement_id}/archive", response_model=AnnouncementRead)
async def archive_announcement(
    announcement_id: str,
    data: AnnouncementArchive,
    ctx: RequestContext = Depends(require(P_ANNOUNCEMENT_ARCHIVE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, announcement_id)
    return await service.archive(session, ctx, obj, data.version)


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: str,
    data: AnnouncementDelete,
    ctx: RequestContext = Depends(require(P_ANNOUNCEMENT_DELETE)),
    session: SessionDep = None,
):
    obj = await service.get_owned(session, ctx, announcement_id)
    await service.delete(session, ctx, obj, data.version)
