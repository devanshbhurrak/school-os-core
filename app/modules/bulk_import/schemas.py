"""Bulk import/export request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.modules.bulk_import.enums import ImportJobStatus, ImportResourceType


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    resource_type: ImportResourceType
    status: ImportJobStatus
    total_rows: int | None
    processed_rows: int
    success_rows: int
    failed_rows: int
    error_summary: list[dict[str, Any]] | None
    original_filename: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ImportJobCreate(BaseModel):
    resource_type: ImportResourceType


class ExportParams(BaseModel):
    resource_type: ImportResourceType
    format: Literal["csv"] = "csv"
