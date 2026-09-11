"""Unit tests for cursor/offset pagination helpers."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.pagination import (
    MAX_OFFSET_TOTAL,
    CursorParams,
    OffsetParams,
    decode_cursor,
    encode_cursor,
)


def test_cursor_round_trip() -> None:
    created_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
    cursor = encode_cursor(created_at, "01HXYZ1234567890ABCDEFGHIJ")
    decoded_created, decoded_id = decode_cursor(cursor)
    assert decoded_id == "01HXYZ1234567890ABCDEFGHIJ"
    assert decoded_created == created_at


@pytest.mark.parametrize(
    "bad",
    ["not-base64", "", "aGVsbG8", "%%%", "eyJmYWtlIjoianNvbiJ9"],
)
def test_decode_malformed_cursor_raises(bad: str) -> None:
    with pytest.raises(ValueError):
        decode_cursor(bad)


def test_cursor_params_defaults_and_bounds() -> None:
    params = CursorParams()
    assert params.limit == 20
    assert params.cursor is None
    with pytest.raises(ValueError):
        CursorParams(limit=0)
    with pytest.raises(ValueError):
        CursorParams(limit=101)


def test_offset_params_cap() -> None:
    assert OffsetParams(page=1, page_size=20).offset == 0
    assert OffsetParams(page=3, page_size=50).offset == 100
    with pytest.raises(ValueError):
        OffsetParams(page=201, page_size=50)  # would exceed MAX_OFFSET_TOTAL


def test_offset_total_constant() -> None:
    assert MAX_OFFSET_TOTAL == 10_000
