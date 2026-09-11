"""Contact request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.people.enums import ContactType

ALLOWED_ENTITY_TYPES = ("PERSON", "SCHOOL")


class ContactBase(BaseModel):
    entity_type: str = Field(min_length=1, max_length=24)
    entity_id: str = Field(min_length=1)
    contact_type: ContactType
    value: str = Field(min_length=1, max_length=255)
    label: str | None = Field(default=None, max_length=60)
    is_primary: bool = False
    is_emergency: bool = False


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    contact_type: ContactType | None = None
    value: str | None = Field(default=None, min_length=1, max_length=255)
    label: str | None = Field(default=None, max_length=60)
    is_primary: bool | None = None
    is_emergency: bool | None = None


class ContactRead(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
