"""Notification routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage
from app.db.session import SessionDep
from app.modules.notifications import service
from app.modules.notifications.permissions import P_NOTIFICATION_LIST, P_NOTIFICATION_UPDATE
from app.modules.notifications.schemas import NotificationListParams, NotificationRead, UnreadCountResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=CursorPage[NotificationRead])
async def list_notifications(
    is_read: bool | None = None,
    type: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    ctx: RequestContext = Depends(require(P_NOTIFICATION_LIST)),
    session: SessionDep = None,
):
    params = NotificationListParams(is_read=is_read, type=type, cursor=cursor, limit=limit)
    page = await service.list_notifications(session, ctx, params)
    page.items = [NotificationRead.model_validate(n) for n in page.items]
    return page


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: str,
    ctx: RequestContext = Depends(require(P_NOTIFICATION_UPDATE)),
    session: SessionDep = None,
):
    notif = await service.mark_read(session, ctx, notification_id)
    return NotificationRead.model_validate(notif)


@router.post("/read-all")
async def mark_all_read(
    ctx: RequestContext = Depends(require(P_NOTIFICATION_UPDATE)),
    session: SessionDep = None,
):
    count = await service.mark_all_read(session, ctx)
    return {"marked": count}


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    ctx: RequestContext = Depends(require(P_NOTIFICATION_LIST)),
    session: SessionDep = None,
):
    return await service.get_unread_count(session, ctx)
