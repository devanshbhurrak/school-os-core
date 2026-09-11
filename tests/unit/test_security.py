"""Unit tests for JWT and refresh-token primitives."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest

from app.core.errors import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)


def test_access_token_round_trip() -> None:
    token = create_access_token("user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert "jti" in payload and payload["jti"]
    assert "exp" in payload and "iat" in payload


def test_access_token_expired() -> None:
    token = create_access_token("user-123", expires_delta=timedelta(seconds=-10))
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_access_token_tampered() -> None:
    token = create_access_token("user-123")
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(AuthenticationError):
        decode_access_token(tampered)


def test_access_token_wrong_secret() -> None:
    payload = {"sub": "x", "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = pyjwt.encode(payload, "x" * 48, algorithm="HS256")
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_refresh_token_generation_and_hash() -> None:
    raw, digest = generate_refresh_token()
    assert len(raw) >= 32
    assert digest == hash_refresh_token(raw)
    assert digest != hash_refresh_token(raw + "x")
    assert len(digest) == 64


def test_refresh_tokens_are_unique() -> None:
    raws = {generate_refresh_token()[0] for _ in range(100)}
    assert len(raws) == 100
