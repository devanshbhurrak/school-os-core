"""Address request/response schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.people.enums import AddressType

ALLOWED_ENTITY_TYPES = ("SCHOOL", "PERSON")


class AddressBase(BaseModel):
    entity_type: str = Field(min_length=1, max_length=24)
    entity_id: str = Field(min_length=1)
    address_type: AddressType = AddressType.RESIDENTIAL
    line1: str | None = Field(default=None, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    landmark: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=16)
    country_code: str = Field(default="IN", max_length=2, min_length=2)
    is_primary: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    address_type: AddressType | None = None
    line1: str | None = Field(default=None, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    landmark: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=16)
    country_code: str | None = Field(default=None, max_length=2, min_length=2)
    is_primary: bool | None = None
    version: int = Field(ge=1)


class AddressRead(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    version: int
    created_at: datetime
    updated_at: datetime
