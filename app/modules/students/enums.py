from enum import StrEnum


class StudentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    GRADUATED = "GRADUATED"
    TRANSFERRED = "TRANSFERRED"
    INACTIVE = "INACTIVE"
    DECEASED = "DECEASED"


class EnrollmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    TRANSFERRED = "TRANSFERRED"
    WITHDRAWN = "WITHDRAWN"
    COMPLETED = "COMPLETED"


class EnrollmentType(StrEnum):
    REGULAR = "REGULAR"
    TRANSFER_IN = "TRANSFER_IN"
    REPEAT = "REPEAT"
    PROMOTION = "PROMOTION"
    TEMPORARY = "TEMPORARY"


class GuardianRelationship(StrEnum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    GUARDIAN = "GUARDIAN"
    GRANDPARENT = "GRANDPARENT"
    SIBLING = "SIBLING"
    OTHER = "OTHER"
