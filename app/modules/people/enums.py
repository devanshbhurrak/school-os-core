"""People module vocabularies."""
from __future__ import annotations

from enum import StrEnum


class AddressType(StrEnum):
    RESIDENTIAL = "RESIDENTIAL"
    PERMANENT = "PERMANENT"
    CORRESPONDENCE = "CORRESPONDENCE"
    CAMPUS = "CAMPUS"
    OTHER = "OTHER"


class ContactType(StrEnum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class PersonStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DECEASED = "DECEASED"
    MERGED = "MERGED"
