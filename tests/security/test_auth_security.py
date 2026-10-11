"""Tests for authentication security measures.

Covers expired tokens, invalid tokens, missing tokens,
and single-use password reset tokens.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.security import create_access_token, hash_refresh_token
from app.modules.auth.models import PasswordResetToken


def auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


async def test_expired_access_token_rejected(seeded_world, client):
    """An expired access token is rejected with 401."""
    token = create_access_token(seeded_world.admin_a.id, expires_delta=timedelta(seconds=-1))
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_invalid_token_rejected(seeded_world, client):
    """A garbage token is rejected."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage.invalid.token"},
    )
    assert resp.status_code == 401


async def test_missing_token_rejected(seeded_world, client):
    """No token results in 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_empty_bearer_rejected(seeded_world, client):
    """An empty Bearer value is rejected."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer "},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Password reset token single-use
# ---------------------------------------------------------------------------


async def test_password_reset_token_single_use(seeded_world, client, migrator_session):
    """A password reset token cannot be used twice."""
    raw = "single-use-token-abcdef0123456789"
    async with migrator_session.begin():
        migrator_session.add(
            PasswordResetToken(
                user_id=seeded_world.admin_a.id,
                token_hash=hash_refresh_token(raw),
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )

    resp1 = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw, "new_password": "NewPass2026!"},
    )
    assert resp1.status_code == 204

    # Second use of the same token must fail.
    resp2 = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw, "new_password": "AnotherPass2026!"},
    )
    assert resp2.status_code in (400, 404, 422)


async def test_expired_password_reset_token_rejected(seeded_world, client, migrator_session):
    """An expired password reset token is rejected."""
    raw = "expired-reset-token-abcdef012345"
    async with migrator_session.begin():
        migrator_session.add(
            PasswordResetToken(
                user_id=seeded_world.admin_a.id,
                token_hash=hash_refresh_token(raw),
                expires_at=datetime.now(UTC) - timedelta(minutes=5),
            )
        )

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw, "new_password": "FreshPass2026!"},
    )
    assert resp.status_code in (400, 404, 422)


# ---------------------------------------------------------------------------
# Refresh token rotation & reuse (theft response)
# ---------------------------------------------------------------------------


async def test_invalid_refresh_token_rejected(seeded_world, client):  # noqa: ARG001
    """A garbage refresh token is rejected with 401."""
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_reused_refresh_token_rejected(seeded_world, client):
    """Reusing a rotated refresh token is rejected and kills the family."""
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": seeded_world.admin_a.email, "password": seeded_world.password},
    )
    assert login.status_code == 200, login.text
    first_refresh = login.json()["refresh_token"]

    rotated = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first_refresh}
    )
    assert rotated.status_code == 200
    second_refresh = rotated.json()["refresh_token"]

    # Reuse of the rotated token → 401 (theft response revokes the family).
    reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first_refresh}
    )
    assert reuse.status_code == 401

    # The family's newest token is dead too.
    dead = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second_refresh}
    )
    assert dead.status_code == 401


# ---------------------------------------------------------------------------
# Brute-force lockout persistence (A7: survives restarts — DB-backed)
# ---------------------------------------------------------------------------


async def test_brute_force_lockout_persists(seeded_world, client, migrator_session):
    """Five failures lock the account; the lockout lives in the DB (not memory)."""
    from sqlalchemy import select

    from app.modules.auth.models import LoginAttempt
    from app.modules.iam.models import User

    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": seeded_world.admin_a.email, "password": "WrongPassword1!"},
        )
        assert resp.status_code == 401

    # Lockout state is a persisted column — a restart cannot clear it.
    user = await migrator_session.scalar(
        select(User).where(User.id == seeded_world.admin_a.id)
    )
    assert user is not None
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(UTC)

    # Failed attempts are durably recorded.
    failures = await migrator_session.scalar(
        select(LoginAttempt).where(
            LoginAttempt.user_id == seeded_world.admin_a.id,
            LoginAttempt.success.is_(False),
        ).order_by(LoginAttempt.attempted_at.desc()).limit(1)
    )
    assert failures is not None

    # Correct credentials are still rejected while locked.
    locked = await client.post(
        "/api/v1/auth/login",
        json={"identifier": seeded_world.admin_a.email, "password": seeded_world.password},
    )
    assert locked.status_code == 401
