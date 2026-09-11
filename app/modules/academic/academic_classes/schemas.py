"""AcademicClass request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.academic.enums import AcademicClassStatus


class AcademicClassCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0)
    status: AcademicClassStatus = AcademicClassStatus.ACTIVE


class AcademicClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None
    status: AcademicClassStatus | None = None
    version: int = Field(ge=1)


class AcademicClassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    code: str
    name: str
    description: str | None = None
    sort_order: int
    status: AcademicClassStatus
    version: int
    created_at: datetime
    updated_at: datetime
