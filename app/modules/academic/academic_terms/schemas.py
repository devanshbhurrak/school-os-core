"""AcademicTerm request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.academic.enums import AcademicTermStatus


class AcademicTermCreate(BaseModel):
    academic_year_id: str = Field(min_length=1)
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    status: AcademicTermStatus = AcademicTermStatus.ACTIVE


class AcademicTermUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    status: AcademicTermStatus | None = None
    version: int = Field(ge=1)


class AcademicTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    academic_year_id: str
    code: str
    name: str
    start_date: date
    end_date: date
    status: AcademicTermStatus
    version: int
    created_at: datetime
    updated_at: datetime
