"""Notification ORM model — org-scoped."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import PKMixin, TimestampMixin
from app.db.types import ULIDType, enum_check
from app.modules.notifications.enums import NotificationType


class Notification(PKMixin, TimestampMixin, Base):
    """A notification delivered to a specific user."""

    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(ULIDType, nullable=False, index=True)
    school_id: Mapped[str | None] = mapped_column(ULIDType, nullable=True)
    organization_id: Mapped[str] = mapped_column(ULIDType, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(ULIDType, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read", "created_at"),
        enum_check("type", NotificationType, "ck_notifications_type"),
    )
