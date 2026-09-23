"""Teacher request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.teachers.enums import AssignmentRole, AssignmentStatus, TeacherStatus


class TeacherCreate(BaseModel):
    person_id: str
    employee_number: str | None = Field(default=None, max_length=50)
    designation: str | None = Field(default=None, max_length=100)
    joining_date: date | None = None
    status: TeacherStatus = TeacherStatus.ACTIVE


class TeacherUpdate(BaseModel):
    employee_number: str | None = Field(default=None, max_length=50)
    designation: str | None = Field(default=None, max_length=100)
    joining_date: date | None = None
    leaving_date: date | None = None
    status: TeacherStatus | None = None
    version: int = Field(ge=1)


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    person_id: str
    employee_number: str | None
    designation: str | None
    joining_date: date | None
    leaving_date: date | None
    status: TeacherStatus
    person_first_name: str
    person_last_name: str | None
    person_primary_email: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class AssignmentCreate(BaseModel):
    teacher_id: str
    cohort_id: str
    subject_id: str | None = None
    academic_year_id: str
    role: AssignmentRole = AssignmentRole.SUBJECT_TEACHER
    start_date: date


class AssignmentUpdate(BaseModel):
    end_date: date | None = None
    status: AssignmentStatus | None = None
    version: int = Field(ge=1)


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    teacher_id: str
    cohort_id: str
    subject_id: str | None
    academic_year_id: str
    role: AssignmentRole
    start_date: date
    end_date: date | None
    status: AssignmentStatus
    teacher_person_first_name: str
    teacher_person_last_name: str | None
    cohort_name: str
    subject_name: str | None
    academic_year_code: str
    version: int
    created_at: datetime
