"""Announcement request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.announcements.enums import (
    AnnouncementPriority,
    AnnouncementPublishMode,
    AnnouncementStatus,
    AnnouncementTargetType,
)


class AnnouncementTargetCreate(BaseModel):
    target_type: AnnouncementTargetType
    target_id: str | None = None


class AnnouncementTargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_type: AnnouncementTargetType
    target_id: str | None


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    publish_mode: AnnouncementPublishMode = AnnouncementPublishMode.IMMEDIATE
    targets: list[AnnouncementTargetCreate] = []
    expires_at: datetime | None = None


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    body: str | None = Field(default=None, min_length=1)
    priority: AnnouncementPriority | None = None
    targets: list[AnnouncementTargetCreate] | None = None
    expires_at: datetime | None = None
    version: int = Field(ge=1)


class AnnouncementPublish(BaseModel):
    published_at: datetime | None = None
    version: int = Field(ge=1)


class AnnouncementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    title: str
    body: str
    priority: AnnouncementPriority
    publish_mode: AnnouncementPublishMode
    published_at: datetime | None
    expires_at: datetime | None
    status: AnnouncementStatus
    targets: list[AnnouncementTargetRead]
    version: int
    created_at: datetime
    updated_at: datetime


class AnnouncementFeedItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    priority: AnnouncementPriority
    status: AnnouncementStatus
    published_at: datetime | None
    expires_at: datetime | None
    targets: list[AnnouncementTargetRead]
