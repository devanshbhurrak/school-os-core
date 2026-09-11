"""Unit tests for Argon2id password hashing."""
from __future__ import annotations

import pytest

from app.core.hashing import check_needs_rehash, hash_password, verify_password


def test_hash_and_verify() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password(hashed, "correct horse battery staple")
    assert not verify_password(hashed, "wrong password")


def test_empty_password_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_verify_never_raises_on_garbage() -> None:
    assert verify_password("not-an-argon2-hash", "anything") is False
    assert verify_password("", "anything") is False


def test_check_needs_rehash() -> None:
    hashed = hash_password("password")
    assert check_needs_rehash(hashed) is False
    assert check_needs_rehash("garbage") is True
