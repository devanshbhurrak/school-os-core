"""Outbox monitoring schemas (read-only)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OutboxEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_name: str
    event_version: int
    organization_id: str | None
    school_id: str | None
    entity_type: str | None
    entity_id: str | None
    status: str
    attempts: int
    next_attempt_at: datetime | None
    processed_at: datetime | None
    last_error: str | None
    locked_by: str | None
    locked_at: datetime | None
    created_at: datetime


class OutboxStatusSummary(BaseModel):
    pending: int
    processing: int
    sent: int
    failed: int
    dead_lettered: int
