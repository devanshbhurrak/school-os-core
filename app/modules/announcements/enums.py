from enum import StrEnum


class AnnouncementPriority(StrEnum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class AnnouncementStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class AnnouncementPublishMode(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    SCHEDULED = "SCHEDULED"


class AnnouncementTargetType(StrEnum):
    SCHOOL = "SCHOOL"
    CLASS = "CLASS"
    COHORT = "COHORT"
    ROLE = "ROLE"
