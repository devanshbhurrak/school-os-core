"""Feature flag read schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FeatureFlagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    organization_id: str | None
    school_id: str | None
    enabled: bool
    description: str | None
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
