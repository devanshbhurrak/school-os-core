"""Membership request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.permissions import DataScope
from app.modules.iam.enums import MembershipStatus


class MembershipCreate(BaseModel):
    user_id: str = Field(min_length=1)
    school_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_default: bool = False
    role_ids: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def _dates_ordered(self) -> MembershipCreate:
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class MembershipUpdate(BaseModel):
    status: MembershipStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_default: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)
    version: int = Field(ge=1)


class RoleGrantCreate(BaseModel):
    role_id: str = Field(min_length=1)
    expires_at: datetime | None = None
    data_scope: DataScope | None = None


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    organization_id: str
    school_id: str | None = None
    status: MembershipStatus
    start_date: date | None = None
    end_date: date | None = None
    is_default: bool
    notes: str | None = None
    role_codes: list[str] = Field(default_factory=list)
    version: int
    created_at: datetime
    updated_at: datetime
