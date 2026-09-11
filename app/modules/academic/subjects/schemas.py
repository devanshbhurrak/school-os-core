"""Subject request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.academic.enums import SubjectStatus, SubjectType


class SubjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    subject_type: SubjectType = SubjectType.CORE
    status: SubjectStatus = SubjectStatus.ACTIVE


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    subject_type: SubjectType | None = None
    status: SubjectStatus | None = None
    version: int = Field(ge=1)


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    code: str
    name: str
    description: str | None = None
    subject_type: SubjectType
    status: SubjectStatus
    version: int
    created_at: datetime
    updated_at: datetime
