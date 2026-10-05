"""Notification request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    school_id: str | None
    organization_id: str
    type: str
    title: str
    body: str | None
    related_entity_type: str | None
    related_entity_id: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationListParams(BaseModel):
    is_read: bool | None = None
    type: str | None = None
    cursor: str | None = None
    limit: int = 20


class UnreadCountResponse(BaseModel):
    count: int
