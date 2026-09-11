"""School request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.iam.enums import SchoolStatus


class SchoolBase(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    short_name: str | None = Field(default=None, max_length=60)
    board: str | None = Field(default=None, max_length=40)
    affiliation_number: str | None = Field(default=None, max_length=60)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=24)


class SchoolCreate(SchoolBase):
    pass


class SchoolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    short_name: str | None = Field(default=None, max_length=60)
    status: SchoolStatus | None = None
    board: str | None = Field(default=None, max_length=40)
    affiliation_number: str | None = Field(default=None, max_length=60)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=24)
    settings: dict[str, Any] | None = None
    version: int = Field(ge=1)


class SchoolRead(SchoolBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    status: SchoolStatus
    timezone: str
    locale: str
    settings: dict[str, Any]
    address_id: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime
