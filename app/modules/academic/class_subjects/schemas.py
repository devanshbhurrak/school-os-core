"""ClassSubject request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClassSubjectCreate(BaseModel):
    academic_class_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    effective_from_year_id: str = Field(min_length=1)
    effective_to_year_id: str | None = None


class ClassSubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    academic_class_id: str
    subject_id: str
    effective_from_year_id: str
    effective_to_year_id: str | None = None
    created_at: datetime
    updated_at: datetime
