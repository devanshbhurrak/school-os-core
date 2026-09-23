"""Attendance enums."""
from enum import StrEnum


class AttendanceSessionStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    AMENDED = "AMENDED"


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"
    HOLIDAY = "HOLIDAY"
