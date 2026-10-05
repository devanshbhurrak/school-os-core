from enum import StrEnum


class ParentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ParentRelationship(StrEnum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    GUARDIAN = "GUARDIAN"
    GRANDPARENT = "GRANDPARENT"
    SIBLING = "SIBLING"
    OTHER = "OTHER"
