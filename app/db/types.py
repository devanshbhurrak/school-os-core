"""Custom SQLAlchemy types.

Primary keys are ULIDs: 26-character Crockford base32 strings that are sortable
by creation time, URL-safe, and free of the B-tree hotspot a random UUID incurs.
"""
from __future__ import annotations

import secrets
import time
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, String, TypeDecorator

# Crockford base32 alphabet (excludes I, L, O, U).
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def gen_ulid() -> str:
    """Generate a 26-char ULID: 48-bit ms timestamp + 80-bit randomness."""
    timestamp = int(time.time() * 1000) & ((1 << 48) - 1)
    randomness = int.from_bytes(secrets.token_bytes(10), "big")
    value = (timestamp << 80) | randomness
    chars: list[str] = []
    for _ in range(26):
        chars.append(_ALPHABET[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


class ULIDType(TypeDecorator[str]):
    """A 26-char ULID stored as VARCHAR(26)."""

    impl = String(26)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> str | None:
        if value is None:
            return None
        value = str(value).upper()
        if len(value) != 26:
            raise ValueError(f"ULID must be 26 characters, got {len(value)}: {value!r}")
        return value

    def process_result_value(self, value: Any, dialect) -> str | None:
        return value


class UTCDateTime(TypeDecorator):
    """TIMESTAMPTZ. All timestamps are stored as UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> Any:
        return value

    def process_result_value(self, value: Any, dialect) -> Any:
        return value


def enum_check(column: str, enum_cls: type, name: str | None = None) -> CheckConstraint:
    """Build a CHECK constraint from a Python enum (VARCHAR + CHECK, not PG enum)."""
    values = ", ".join(repr(member.value) for member in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=name or f"ck_{column}")
