"""Announcements ORM models — school-scoped."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, SoftDeleteMixin, TimestampMixin, VersionMixin
from app.db.types import ULIDType, enum_check
from app.modules.announcements.enums import (
    AnnouncementPriority,
    AnnouncementPublishMode,
    AnnouncementStatus,
    AnnouncementTargetType,
)


class Announcement(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A school-wide or targeted announcement."""

    __tablename__ = "announcements"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AnnouncementPriority.NORMAL.value,
        server_default=AnnouncementPriority.NORMAL.value,
    )
    publish_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AnnouncementPublishMode.IMMEDIATE.value,
        server_default=AnnouncementPublishMode.IMMEDIATE.value,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AnnouncementStatus.DRAFT.value,
        server_default=AnnouncementStatus.DRAFT.value,
    )

    targets: Mapped[list[AnnouncementTarget]] = relationship(
        "AnnouncementTarget",
        back_populates="announcement",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (
        enum_check("priority", AnnouncementPriority, "ck_announcements_priority"),
        enum_check("publish_mode", AnnouncementPublishMode, "ck_announcements_publish_mode"),
        enum_check("status", AnnouncementStatus, "ck_announcements_status"),
        Index("ix_announcements_school_status_published", "school_id", "status", "published_at"),
    )


class AnnouncementTarget(PKMixin, TimestampMixin, Base):
    """A targeting rule for an announcement."""

    __tablename__ = "announcement_targets"

    announcement_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str | None] = mapped_column(ULIDType, nullable=True)
    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )

    announcement: Mapped[Announcement] = relationship(
        "Announcement", back_populates="targets"
    )

    __table_args__ = (
        enum_check("target_type", AnnouncementTargetType, "ck_announcement_targets_target_type"),
    )
