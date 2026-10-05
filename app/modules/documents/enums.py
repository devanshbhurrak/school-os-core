"""Document enums."""
from enum import StrEnum


class DocumentStatus(StrEnum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    CONFIRMED = "CONFIRMED"
    DELETED = "DELETED"


class DocumentEntityType(StrEnum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    PARENT = "PARENT"
    SCHOOL = "SCHOOL"


class DocumentType(StrEnum):
    PHOTO = "PHOTO"
    ID_PROOF = "ID_PROOF"
    BIRTH_CERTIFICATE = "BIRTH_CERTIFICATE"
    CERTIFICATE = "CERTIFICATE"
    TRANSCRIPT = "TRANSCRIPT"
    REPORT_CARD = "REPORT_CARD"
    OTHER = "OTHER"
