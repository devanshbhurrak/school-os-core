"""Bulk import enums."""
from __future__ import annotations

from enum import StrEnum


class ImportJobStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"  # some rows failed


class ImportResourceType(StrEnum):
    STUDENTS = "students"
    TEACHERS = "teachers"
