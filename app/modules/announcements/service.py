"""Announcement business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.announcements import repository
from app.modules.announcements.enums import AnnouncementStatus
from app.modules.announcements.models import Announcement
from app.modules.announcements.schemas import AnnouncementCreate, AnnouncementPublish, AnnouncementUpdate
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["title", "priority", "publish_mode", "status", "published_at", "expires_at"]


def _snap(a: Announcement) -> dict:
    return snapshot(a, _SNAPSHOT_FIELDS)


async def get_owned(session: AsyncSession, ctx: RequestContext, announcement_id: str) -> Announcement:
    if ctx.school_id is None:
        raise NotFoundError("The announcement was not found.", code="ANNOUNCEMENT_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, announcement_id)
    if obj is None:
        raise NotFoundError("The announcement was not found.", code="ANNOUNCEMENT_NOT_FOUND")
    return obj


async def create(session: AsyncSession, ctx: RequestContext, data: AnnouncementCreate) -> Announcement:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    instance = Announcement(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        title=data.title,
        body=data.body,
        priority=data.priority,
        publish_mode=data.publish_mode,
        expires_at=data.expires_at,
        status=AnnouncementStatus.DRAFT,
    )
    session.add(instance)
    await session.flush()

    if data.targets:
        await repository.replace_targets(
            session, instance.id, ctx.school_id, ctx.organization_id, data.targets
        )

    await audit(
        session, ctx,
        action="ANNOUNCEMENT_CREATED",
        entity_type="announcement",
        entity_id=instance.id,
        summary=f"Announcement {instance.title!r} created",
        after=_snap(instance),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    announcement: Announcement,
    data: AnnouncementUpdate,
) -> Announcement:
    if announcement.version != data.version:
        raise StaleResourceError()

    before = _snap(announcement)
    payload = data.model_dump(exclude={"version", "targets"}, exclude_none=True)
    for field, value in payload.items():
        setattr(announcement, field, value)
    announcement.updated_by_id = ctx.user_id
    await session.flush()

    if data.targets is not None:
        await repository.replace_targets(
            session, announcement.id, announcement.school_id, announcement.organization_id, data.targets
        )

    await audit(
        session, ctx,
        action="ANNOUNCEMENT_UPDATED",
        entity_type="announcement",
        entity_id=announcement.id,
        summary=f"Announcement {announcement.title!r} updated",
        before=before,
        after=_snap(announcement),
    )
    return announcement


async def publish(
    session: AsyncSession,
    ctx: RequestContext,
    announcement: Announcement,
    data: AnnouncementPublish,
) -> Announcement:
    if announcement.version != data.version:
        raise StaleResourceError()

    if announcement.status != AnnouncementStatus.DRAFT:
        raise InvalidRequestError(
            "Only DRAFT announcements can be published.",
            code="ANNOUNCEMENT_NOT_DRAFT",
        )

    before = _snap(announcement)
    announcement.published_at = data.published_at or datetime.now(UTC)
    announcement.status = AnnouncementStatus.PUBLISHED
    announcement.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ANNOUNCEMENT_PUBLISHED",
        entity_type="announcement",
        entity_id=announcement.id,
        summary=f"Announcement {announcement.title!r} published",
        before=before,
        after=_snap(announcement),
    )
    return announcement


async def archive(
    session: AsyncSession,
    ctx: RequestContext,
    announcement: Announcement,
    version: int,
) -> Announcement:
    if announcement.version != version:
        raise StaleResourceError()

    before = _snap(announcement)
    announcement.status = AnnouncementStatus.ARCHIVED
    announcement.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ANNOUNCEMENT_ARCHIVED",
        entity_type="announcement",
        entity_id=announcement.id,
        summary=f"Announcement {announcement.title!r} archived",
        before=before,
        after=_snap(announcement),
    )
    return announcement


async def delete(
    session: AsyncSession,
    ctx: RequestContext,
    announcement: Announcement,
    version: int,
) -> None:
    if announcement.status != AnnouncementStatus.DRAFT:
        raise InvalidRequestError(
            "Only DRAFT announcements can be deleted.",
            code="ANNOUNCEMENT_NOT_DRAFT",
        )
    if announcement.version != version:
        raise StaleResourceError()

    before = _snap(announcement)
    announcement.deleted_at = datetime.now(UTC)
    announcement.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ANNOUNCEMENT_DELETED",
        entity_type="announcement",
        entity_id=announcement.id,
        summary=f"Announcement {announcement.title!r} deleted",
        before=before,
    )
