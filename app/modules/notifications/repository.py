"""Notification data access — org-scoped, user-filtered."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationListParams


async def list_for_user(
    session: AsyncSession,
    user_id: str,
    org_id: str,
    params: NotificationListParams,
) -> CursorPage[Notification]:
    stmt = select(Notification).where(
        Notification.user_id == user_id,
        Notification.organization_id == org_id,
    )
    if params.is_read is not None:
        stmt = stmt.where(Notification.is_read == params.is_read)
    if params.type is not None:
        stmt = stmt.where(Notification.type == params.type)

    cursor_params = CursorParams(cursor=params.cursor, limit=params.limit)
    return await paginate_cursor(session, stmt, cursor_params, model=Notification)


async def get_by_id(
    session: AsyncSession, notification_id: str, user_id: str
) -> Notification | None:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    return (await session.scalars(stmt)).first()


async def mark_read(
    session: AsyncSession, notification_id: str, user_id: str
) -> Notification | None:
    notif = await get_by_id(session, notification_id, user_id)
    if notif is None:
        return None
    notif.is_read = True
    notif.read_at = datetime.now(UTC)
    await session.flush()
    return notif


async def mark_all_read(
    session: AsyncSession, user_id: str, org_id: str
) -> int:
    result = await session.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.organization_id == org_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=datetime.now(UTC))
    )
    await session.flush()
    return result.rowcount  # type: ignore[return-value]


async def count_unread(
    session: AsyncSession, user_id: str, org_id: str
) -> int:
    result = await session.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.organization_id == org_id,
            Notification.is_read.is_(False),
        )
    )
    return int(result or 0)
