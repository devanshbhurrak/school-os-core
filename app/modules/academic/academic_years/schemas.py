"""AcademicYear request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.academic.enums import AcademicYearStatus


class AcademicYearCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    is_current: bool = False
    status: AcademicYearStatus = AcademicYearStatus.DRAFT


class AcademicYearUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    status: AcademicYearStatus | None = None
    version: int = Field(ge=1)


class AcademicYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    code: str
    name: str
    start_date: date
    end_date: date
    is_current: bool
    status: AcademicYearStatus
    version: int
    created_at: datetime
    updated_at: datetime
