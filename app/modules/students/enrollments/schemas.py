"""Enrollment request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.students.enums import EnrollmentStatus, EnrollmentType


class EnrollmentCreate(BaseModel):
    student_id: str
    academic_year_id: str
    academic_class_id: str
    cohort_id: str
    roll_number: str | None = Field(default=None, max_length=20)
    start_date: date
    enrollment_type: EnrollmentType = EnrollmentType.REGULAR


class EnrollmentUpdate(BaseModel):
    roll_number: str | None = Field(default=None, max_length=20)
    end_date: date | None = None
    status: EnrollmentStatus | None = None
    version: int = Field(ge=1)


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    student_id: str
    academic_year_id: str
    academic_class_id: str
    cohort_id: str
    roll_number: str | None
    start_date: date
    end_date: date | None
    enrollment_type: EnrollmentType
    status: EnrollmentStatus
    version: int
    created_at: datetime
    updated_at: datetime

    # Denormalized fields
    student_name: str | None = None
    cohort_name: str | None = None
    academic_year_name: str | None = None

    @classmethod
    def from_orm_with_relations(cls, enrollment: object) -> "EnrollmentRead":
        data = cls.model_validate(enrollment)
        student = getattr(enrollment, "student", None)
        if student is not None:
            person = getattr(student, "person", None)
            if person is not None:
                first = getattr(person, "first_name", "") or ""
                last = getattr(person, "last_name", None)
                data.student_name = " ".join(filter(None, [first, last])) or None
        cohort = getattr(enrollment, "cohort", None)
        if cohort is not None:
            data.cohort_name = getattr(cohort, "name", None)
        academic_year = getattr(enrollment, "academic_year", None)
        if academic_year is not None:
            data.academic_year_name = getattr(academic_year, "name", None)
        return data


class EnrollmentTransfer(BaseModel):
    new_cohort_id: str
    new_academic_class_id: str
    effective_date: date
    reason: str | None = Field(default=None, max_length=500)
