"""Pagination: keyset (cursor) by default, offset opt-in and capped.

Cursor pagination is stable under concurrent inserts — no skipped or repeated
rows — and pages as fast on page 900 as on page 1. `total` is optional because
`COUNT(*)` over a large filtered table is the most common source of slow list
endpoints.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")

MAX_PAGE_SIZE = 100
MAX_OFFSET_TOTAL = 10_000


class CursorParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=MAX_PAGE_SIZE)
    cursor: str | None = None


class OffsetParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=MAX_PAGE_SIZE)

    @model_validator(mode="after")
    def _cap_offset(self) -> OffsetParams:
        if (self.page - 1) * self.page_size >= MAX_OFFSET_TOTAL:
            raise ValueError(f"Offset pagination is capped at {MAX_OFFSET_TOTAL} rows.")
        return self

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False


class OffsetPage(BaseModel, Generic[T]):
    items: list[T]
    total: int | None = None  # None means not computed
    page: int
    page_size: int


def encode_cursor(created_at: datetime, row_id: str) -> str:
    payload = json.dumps([created_at.isoformat(), str(row_id)]).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    """Decode a cursor; raises ValueError when the cursor is malformed."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        created_at_iso, row_id = json.loads(raw.decode("utf-8"))
        created_at = datetime.fromisoformat(created_at_iso)
        return created_at, str(row_id)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Malformed cursor.") from exc
