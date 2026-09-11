"""Academic domain lifecycle enums."""
from __future__ import annotations

from enum import StrEnum


class AcademicYearStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class AcademicTermStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class AcademicClassStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class SubjectType(StrEnum):
    CORE = "CORE"
    OPTIONAL = "OPTIONAL"
    ELECTIVE = "ELECTIVE"
    PRACTICAL = "PRACTICAL"
    CO_CURRICULAR = "CO_CURRICULAR"
    ACTIVITY = "ACTIVITY"


class SubjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class CohortStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
