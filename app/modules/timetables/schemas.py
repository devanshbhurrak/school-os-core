"""Timetable request/response schemas."""
from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.modules.timetables.enums import DayOfWeek, PeriodType, TimetableSlotStatus


# ---------------------------------------------------------------------------
# Period Definitions
# ---------------------------------------------------------------------------


class PeriodDefinitionCreate(BaseModel):
    academic_year_id: str
    name: str = Field(max_length=50)
    period_type: PeriodType = PeriodType.LESSON
    start_time: time
    end_time: time
    sort_order: int = 0


class PeriodDefinitionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    period_type: PeriodType | None = None
    start_time: time | None = None
    end_time: time | None = None
    sort_order: int | None = None


class PeriodDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    academic_year_id: str
    name: str
    period_type: PeriodType
    start_time: time
    end_time: time
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Timetable Slots
# ---------------------------------------------------------------------------


class TimetableSlotCreate(BaseModel):
    cohort_id: str
    period_definition_id: str
    teacher_id: str
    subject_id: str
    day_of_week: DayOfWeek
    effective_from: date
    effective_to: date | None = None
    notes: str | None = None


class TimetableSlotUpdate(BaseModel):
    teacher_id: str | None = None
    subject_id: str | None = None
    effective_to: date | None = None
    status: TimetableSlotStatus | None = None
    notes: str | None = None
    version: int = Field(ge=1)


class TimetableSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    academic_year_id: str
    cohort_id: str
    period_definition_id: str
    teacher_id: str
    subject_id: str
    day_of_week: DayOfWeek
    effective_from: date
    effective_to: date | None
    status: TimetableSlotStatus
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    # Denormalized display fields
    teacher_name: str | None = None
    subject_name: str | None = None
    cohort_name: str | None = None
    period_name: str | None = None
