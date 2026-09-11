"""Audit log read schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None = None
    school_id: str | None = None
    actor_user_id: str | None = None
    actor_label: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    summary: str | None = None
    before_snapshot: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None
    context: dict[str, Any] = {}
    request_id: str | None = None
    ip_address: str | None = None
    created_at: datetime
    updated_at: datetime
