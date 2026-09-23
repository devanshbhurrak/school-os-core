"""Announcement data access — school-scoped."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.db.types import gen_ulid
from app.modules.announcements.enums import AnnouncementPriority, AnnouncementStatus
from app.modules.announcements.models import Announcement, AnnouncementTarget
from app.modules.announcements.schemas import AnnouncementTargetCreate


async def get_by_id(
    session: AsyncSession,
    school_id: str,
    announcement_id: str,
) -> Announcement | None:
    stmt = (
        select(Announcement)
        .where(
            Announcement.id == announcement_id,
            Announcement.school_id == school_id,
            Announcement.deleted_at.is_(None),
        )
        .options(selectinload(Announcement.targets))
    )
    return (await session.scalars(stmt)).first()


async def list_announcements(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
    status: AnnouncementStatus | None = None,
    priority: AnnouncementPriority | None = None,
) -> CursorPage[Announcement]:
    stmt = select(Announcement).where(
        Announcement.school_id == school_id,
        Announcement.deleted_at.is_(None),
    )
    if status is not None:
        stmt = stmt.where(Announcement.status == status)
    if priority is not None:
        stmt = stmt.where(Announcement.priority == priority)
    return await paginate_cursor(session, stmt, params, model=Announcement)


async def replace_targets(
    session: AsyncSession,
    announcement_id: str,
    school_id: str,
    organization_id: str,
    targets: list[AnnouncementTargetCreate],
) -> None:
    """Delete all existing targets for an announcement and insert the new ones."""
    await session.execute(
        delete(AnnouncementTarget).where(
            AnnouncementTarget.announcement_id == announcement_id
        )
    )
    for t in targets:
        session.add(
            AnnouncementTarget(
                id=gen_ulid(),
                announcement_id=announcement_id,
                target_type=t.target_type,
                target_id=t.target_id,
                school_id=school_id,
                organization_id=organization_id,
            )
        )


async def list_feed(
    session: AsyncSession,
    school_id: str,
    params: CursorParams,
) -> CursorPage[Announcement]:
    """Published, non-expired announcements ordered newest-first."""
    now = datetime.now(UTC)
    stmt = select(Announcement).where(
        Announcement.school_id == school_id,
        Announcement.deleted_at.is_(None),
        Announcement.status == AnnouncementStatus.PUBLISHED,
        or_(Announcement.expires_at.is_(None), Announcement.expires_at > now),
    )
    return await paginate_cursor(session, stmt, params, model=Announcement)
