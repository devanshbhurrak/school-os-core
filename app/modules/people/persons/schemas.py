"""Person request/response schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.people.enums import PersonStatus


class PersonCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=24)
    blood_group: str | None = Field(default=None, max_length=8)
    nationality: str | None = Field(default=None, max_length=60)
    primary_phone: str | None = Field(default=None, max_length=24)
    primary_email: str | None = Field(default=None, max_length=255)
    address_id: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class PersonUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=24)
    blood_group: str | None = Field(default=None, max_length=8)
    nationality: str | None = Field(default=None, max_length=60)
    primary_phone: str | None = Field(default=None, max_length=24)
    primary_email: str | None = Field(default=None, max_length=255)
    address_id: str | None = None
    custom_fields: dict[str, Any] | None = None
    version: int = Field(ge=1)


class PersonMerge(BaseModel):
    target_person_id: str = Field(min_length=1)
    version: int = Field(ge=1)


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    first_name: str
    middle_name: str | None = None
    last_name: str | None = None
    preferred_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None
    nationality: str | None = None
    primary_phone: str | None = None
    primary_email: str | None = None
    address_id: str | None = None
    status: PersonStatus
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    version: int
    created_at: datetime
    updated_at: datetime
