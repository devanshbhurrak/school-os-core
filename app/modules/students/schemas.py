"""Student request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.students.enums import StudentStatus


class StudentCreate(BaseModel):
    person_id: str
    admission_number: str = Field(min_length=1, max_length=50)
    admission_date: date
    status: StudentStatus = StudentStatus.ACTIVE


class StudentUpdate(BaseModel):
    admission_number: str | None = Field(default=None, min_length=1, max_length=50)
    admission_date: date | None = None
    status: StudentStatus | None = None
    withdrawal_date: date | None = None
    withdrawal_reason: str | None = Field(default=None, max_length=500)
    version: int = Field(ge=1)


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    person_id: str
    admission_number: str
    admission_date: date
    status: StudentStatus
    withdrawal_date: date | None
    withdrawal_reason: str | None
    version: int
    created_at: datetime
    updated_at: datetime

    # Denormalized from Person relationship
    person_first_name: str = ""
    person_last_name: str | None = None
    person_primary_email: str | None = None
    person_primary_phone: str | None = None

    @classmethod
    def from_orm_with_person(cls, student: object) -> "StudentRead":
        person = getattr(student, "person", None)
        data = cls.model_validate(student)
        if person is not None:
            data.person_first_name = getattr(person, "first_name", "")
            data.person_last_name = getattr(person, "last_name", None)
            data.person_primary_email = getattr(person, "primary_email", None)
            data.person_primary_phone = getattr(person, "primary_phone", None)
        return data
