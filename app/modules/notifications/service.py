"""Notification business logic."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import NotFoundError
from app.core.pagination import CursorPage
from app.modules.notifications import repository
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationListParams, UnreadCountResponse


async def list_notifications(
    session: AsyncSession, ctx: RequestContext, params: NotificationListParams
) -> CursorPage[Notification]:
    return await repository.list_for_user(session, ctx.user_id, ctx.organization_id, params)


async def mark_read(
    session: AsyncSession, ctx: RequestContext, notification_id: str
) -> Notification:
    notif = await repository.mark_read(session, notification_id, ctx.user_id)
    if notif is None:
        raise NotFoundError("The notification was not found.", code="NOTIFICATION_NOT_FOUND")
    return notif


async def mark_all_read(session: AsyncSession, ctx: RequestContext) -> int:
    return await repository.mark_all_read(session, ctx.user_id, ctx.organization_id)


async def get_unread_count(session: AsyncSession, ctx: RequestContext) -> UnreadCountResponse:
    count = await repository.count_unread(session, ctx.user_id, ctx.organization_id)
    return UnreadCountResponse(count=count)


async def create_notification(
    session: AsyncSession,
    *,
    user_id: str,
    org_id: str,
    school_id: str | None = None,
    type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> Notification:
    instance = Notification(
        user_id=user_id,
        organization_id=org_id,
        school_id=school_id,
        type=type,
        title=title,
        body=body,
        related_entity_type=entity_type,
        related_entity_id=entity_id,
    )
    session.add(instance)
    await session.flush()
    return instance
