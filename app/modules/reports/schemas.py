"""Report request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExportRequest(BaseModel):
    report_type: str
    filters: dict | None = None


class ExportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    report_type: str
    status: str
    filters: dict | None
    row_count: int | None
    storage_key: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by_id: str | None


class ExportJobListParams(BaseModel):
    status: str | None = None
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
