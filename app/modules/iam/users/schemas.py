"""User request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.modules.iam.enums import MembershipStatus, UserStatus


class UserCreate(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=24)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    school_id: str | None = None

    @model_validator(mode="after")
    def _require_identifier(self) -> UserCreate:
        if not self.email and not self.phone:
            raise ValueError("Provide an email or a phone number.")
        return self


class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=24)
    status: UserStatus | None = None
    must_change_password: bool | None = None
    version: int = Field(ge=1)


class MembershipBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    school_id: str | None = None
    status: MembershipStatus
    is_default: bool
    start_date: Any | None = None
    end_date: Any | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    person_id: str | None = None
    email: str | None = None
    email_verified_at: datetime | None = None
    phone: str | None = None
    phone_verified_at: datetime | None = None
    status: UserStatus
    must_change_password: bool
    is_platform_admin: bool
    last_login_at: datetime | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    memberships: list[MembershipBrief] = Field(default_factory=list)
