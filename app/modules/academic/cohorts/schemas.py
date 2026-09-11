"""Cohort request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.academic.enums import CohortStatus


class CohortCreate(BaseModel):
    academic_year_id: str = Field(min_length=1)
    academic_class_id: str = Field(min_length=1)
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    capacity: int | None = Field(default=None, ge=1)
    status: CohortStatus = CohortStatus.ACTIVE


class CohortUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    capacity: int | None = Field(default=None, ge=1)
    status: CohortStatus | None = None
    version: int = Field(ge=1)


class CohortRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    academic_year_id: str
    academic_class_id: str
    code: str
    name: str
    capacity: int | None = None
    status: CohortStatus
    version: int
    created_at: datetime
    updated_at: datetime
