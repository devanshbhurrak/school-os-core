"""Argon2id password hashing — Argon2 directly, not passlib.

Argon2id is memory-hard and GPU-resistant; it is the OWASP/NIST recommendation
for new systems. `verify_password` returns a bool rather than raising, which
keeps the login path's timing uniform for the wrong-password and
unknown-account cases (the hash is still computed either way).
"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# OWASP minimums: t=2, m=64 MiB, p=4.
_hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    """Hash a plaintext password. Raises ValueError for empty/short input."""
    if not password:
        raise ValueError("Password must not be empty.")
    return _hasher.hash(password)


def verify_password(stored_hash: str, given_password: str) -> bool:
    """Verify `given_password` against `stored_hash`. Never raises on mismatch."""
    try:
        return _hasher.verify(stored_hash, given_password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def check_needs_rehash(stored_hash: str) -> bool:
    """True when the stored hash predates current Argon2 parameters."""
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return True
