"""Role request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.permissions import DataScope
from app.modules.iam.enums import RoleScopeLevel


class RoleBase(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    scope_level: RoleScopeLevel = RoleScopeLevel.SCHOOL
    data_scope: DataScope = DataScope.SCHOOL


class RoleCreate(RoleBase):
    permission_codes: list[str] = Field(default_factory=list, max_length=200)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    data_scope: DataScope | None = None
    permission_codes: list[str] | None = Field(default=None, max_length=200)
    version: int = Field(ge=1)


class RoleRead(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None = None
    is_system: bool
    is_default: bool
    permission_codes: list[str] = Field(default_factory=list)
    version: int
    created_at: datetime
    updated_at: datetime
