from enum import StrEnum


class TeacherStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    RESIGNED = "RESIGNED"
    TERMINATED = "TERMINATED"
    INACTIVE = "INACTIVE"


class AssignmentRole(StrEnum):
    SUBJECT_TEACHER = "SUBJECT_TEACHER"
    CLASS_TEACHER = "CLASS_TEACHER"
    SUBSTITUTE = "SUBSTITUTE"
    COORDINATOR = "COORDINATOR"


class AssignmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
