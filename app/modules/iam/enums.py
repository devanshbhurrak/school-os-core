"""Lifecycle vocabularies for the IAM domain.

Enums are stored as VARCHAR + CHECK constraints (see `app/db/types.enum_check`),
not native PostgreSQL enums, so vocabularies can grow per deployment with a
one-line migration instead of `ALTER TYPE ... ADD VALUE`.
"""
from __future__ import annotations

from enum import StrEnum


class OrganizationStatus(StrEnum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class SchoolStatus(StrEnum):
    SETUP = "SETUP"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class UserStatus(StrEnum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class MembershipStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ENDED = "ENDED"


class RoleScopeLevel(StrEnum):
    """Where a role may be granted: platform-wide, org-wide, or per school."""

    PLATFORM = "PLATFORM"
    ORGANIZATION = "ORGANIZATION"
    SCHOOL = "SCHOOL"


