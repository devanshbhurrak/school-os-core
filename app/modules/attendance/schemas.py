"""Attendance request/response schemas."""
from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.modules.attendance.enums import AttendanceSessionStatus, AttendanceStatus


class AttendanceSessionCreate(BaseModel):
    cohort_id: str
    academic_year_id: str
    session_date: date
    notes: str | None = None


class AttendanceSessionUpdate(BaseModel):
    notes: str | None = None
    status: AttendanceSessionStatus | None = None
    version: int = Field(ge=1)


class AttendanceSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    cohort_id: str
    academic_year_id: str
    session_date: date
    status: AttendanceSessionStatus
    submitted_at: datetime | None
    submitted_by_id: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    created_by_id: str | None
    updated_by_id: str | None

    record_count: int | None = None


class AttendanceRecordUpdate(BaseModel):
    status: AttendanceStatus
    arrived_at: time | None = None
    notes: str | None = None


class AttendanceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    session_id: str
    enrollment_id: str
    student_id: str
    status: AttendanceStatus
    arrived_at: time | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    student_name: str | None = None


class BulkRecordItem(BaseModel):
    enrollment_id: str
    status: AttendanceStatus
    arrived_at: time | None = None
    notes: str | None = None


class BulkRecordUpdate(BaseModel):
    records: list[BulkRecordItem]


class SessionSubmit(BaseModel):
    version: int = Field(ge=1)


class SessionAmend(BaseModel):
    version: int = Field(ge=1)
