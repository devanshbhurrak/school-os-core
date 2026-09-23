from enum import StrEnum


class DayOfWeek(StrEnum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class PeriodType(StrEnum):
    LESSON = "LESSON"
    BREAK = "BREAK"
    LUNCH = "LUNCH"
    ASSEMBLY = "ASSEMBLY"
    FREE = "FREE"
    EXAM = "EXAM"


class TimetableSlotStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    SUBSTITUTED = "SUBSTITUTED"
