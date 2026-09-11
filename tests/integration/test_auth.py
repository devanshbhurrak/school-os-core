"""Auth flows against a live database and the RLS-enforced app session."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import create_access_token, hash_refresh_token
from app.modules.auth.models import PasswordResetToken, RefreshToken
from app.modules.iam.models import User


def auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def _login(client, identifier: str, password: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )


async def test_login_success(seeded_world, client):
    resp = await _login(client, seeded_world.admin_a.email, seeded_world.password)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["id"] == seeded_world.admin_a.id
    assert body["user"]["email"] == seeded_world.admin_a.email


async def test_login_failures_are_uniform(seeded_world, client):
    wrong_password = await _login(client, seeded_world.admin_a.email, "WrongPassword1!")
    unknown_user = await _login(client, "nobody@test.local", seeded_world.password)

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json()["error"]["code"] == "UNAUTHORIZED"
    assert unknown_user.json()["error"]["code"] == "UNAUTHORIZED"
    assert wrong_password.json()["error"]["message"] == unknown_user.json()["error"]["message"]


async def test_suspended_account_cannot_login(seeded_world, client):
    resp = await _login(client, seeded_world.suspended_user.email, seeded_world.password)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ACCOUNT_INACTIVE"


async def test_account_lockout_after_five_failures(seeded_world, client, migrator_session):
    for _ in range(5):
        resp = await _login(client, seeded_world.admin_a.email, "WrongPassword1!")
        assert resp.status_code == 401

    user = await migrator_session.scalar(
        select(User).where(User.id == seeded_world.admin_a.id)
    )
    assert user.locked_until is not None
    assert user.failed_login_count == 0

    # Correct credentials are still rejected while the account is locked.
    locked = await _login(client, seeded_world.admin_a.email, seeded_world.password)
    assert locked.status_code == 401


async def test_refresh_token_rotation_revokes_family(seeded_world, client, migrator_session):
    login = await _login(client, seeded_world.admin_a.email, seeded_world.password)
    refresh_token = login.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200
    new_refresh = first.json()["refresh_token"]

    # Reuse of a rotated token is treated as theft: the whole family dies.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401

    family = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert family.status_code == 401

    rows = list(
        (
            await migrator_session.scalars(
                select(RefreshToken).where(RefreshToken.user_id == seeded_world.admin_a.id)
            )
        ).all()
    )
    assert rows
    assert all(row.revoked_at is not None for row in rows)


async def test_logout_revokes_refresh_token(seeded_world, client):
    login = await _login(client, seeded_world.admin_a.email, seeded_world.password)
    refresh_token = login.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 204

    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401


async def test_password_reset_confirm(seeded_world, client, migrator_session):
    raw = "reset-token-0123456789abcdef"
    async with migrator_session.begin():
        migrator_session.add(
            PasswordResetToken(
                user_id=seeded_world.admin_a.id,
                token_hash=hash_refresh_token(raw),
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )

    old_login = await _login(client, seeded_world.admin_a.email, seeded_world.password)
    assert old_login.status_code == 200

    confirm = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw, "new_password": "FreshPassword2026!"},
    )
    assert confirm.status_code == 204

    stale = await _login(client, seeded_world.admin_a.email, seeded_world.password)
    assert stale.status_code == 401

    fresh = await _login(client, seeded_world.admin_a.email, "FreshPassword2026!")
    assert fresh.status_code == 200


async def test_password_change_revokes_sessions(seeded_world, client):
    login = await _login(client, seeded_world.admin_a.email, seeded_world.password)
    refresh_token = login.json()["refresh_token"]

    change = await client.post(
        "/api/v1/auth/password/change",
        json={"current_password": seeded_world.password, "new_password": "NewPassword2026!"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert change.status_code == 204

    old_session = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert old_session.status_code == 401

    old_login = await _login(client, seeded_world.admin_a.email, seeded_world.password)
    assert old_login.status_code == 401

    new_login = await _login(client, seeded_world.admin_a.email, "NewPassword2026!")
    assert new_login.status_code == 200


async def test_me_reflects_principal(seeded_world, client):
    resp = await client.get("/api/v1/auth/me", headers=auth_header(seeded_world.admin_a.id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == seeded_world.admin_a.id
    assert body["organization_id"] == seeded_world.org_a_id
    assert body["school_id"] == seeded_world.school_a1_id
    assert "iam.organization.create" in body["permissions"]


async def test_suspended_user_token_is_rejected(seeded_world, client):
    resp = await client.get(
        "/api/v1/auth/me", headers=auth_header(seeded_world.suspended_user.id)
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ACCOUNT_INACTIVE"
