"""Guardian request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.students.enums import GuardianRelationship


class GuardianCreate(BaseModel):
    student_id: str
    guardian_person_id: str
    relationship: GuardianRelationship
    is_primary: bool = False
    is_emergency_contact: bool = False
    can_pickup: bool = True


class GuardianUpdate(BaseModel):
    relationship: GuardianRelationship | None = None
    is_primary: bool | None = None
    is_emergency_contact: bool | None = None
    can_pickup: bool | None = None


class GuardianRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    student_id: str
    guardian_person_id: str
    relationship: GuardianRelationship
    is_primary: bool
    is_emergency_contact: bool
    can_pickup: bool
    created_at: datetime
    updated_at: datetime

    # Denormalized from Person relationship
    guardian_first_name: str = ""
    guardian_last_name: str | None = None
    guardian_email: str | None = None
    guardian_phone: str | None = None

    @classmethod
    def from_orm_with_person(cls, guardian: object) -> "GuardianRead":
        person = getattr(guardian, "guardian_person", None)
        data = cls.model_validate(guardian)
        if person is not None:
            data.guardian_first_name = getattr(person, "first_name", "")
            data.guardian_last_name = getattr(person, "last_name", None)
            data.guardian_email = getattr(person, "primary_email", None)
            data.guardian_phone = getattr(person, "primary_phone", None)
        return data
