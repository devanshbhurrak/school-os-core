"""Audit log list/read scoping (RLS-exempt: enforced in the repository) and
`/auth/me` must_change_password flag."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.iam.models import User
from app.modules.platform_.models import AuditLog


def auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _audit_row(
    organization_id: str | None,
    school_id: str | None,
    *,
    actor_user_id: str | None = None,
    action: str = "PERSON_UPDATED",
    entity_type: str = "person",
    summary: str = "Updated a person",
) -> AuditLog:
    return AuditLog(
        organization_id=organization_id,
        school_id=school_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id="entity-1",
        summary=summary,
        request_id="req-1",
        created_at=datetime.now(UTC) - timedelta(minutes=1),
    )


async def _seed_audit_logs(session, seeded_world) -> dict[str, str]:
    rows = {
        "a1": _audit_row(
            seeded_world.org_a_id, seeded_world.school_a1_id, action="SCHOOL_UPDATED"
        ),
        "a2": _audit_row(
            seeded_world.org_a_id, seeded_world.school_a2_id, action="SCHOOL_UPDATED"
        ),
        "b1": _audit_row(
            seeded_world.org_b_id, seeded_world.school_b1_id, action="SCHOOL_UPDATED"
        ),
    }
    session.add_all(rows.values())
    await session.flush()
    ids = {key: row.id for key, row in rows.items()}
    await session.commit()
    return ids


async def test_me_exposes_must_change_password(seeded_world, client, migrator_session):
    async with migrator_session.begin():
        user = await migrator_session.scalar(
            select(User).where(User.id == seeded_world.admin_a.id)
        )
        user.must_change_password = True

    resp = await client.get(
        "/api/v1/auth/me", headers=auth_header(seeded_world.admin_a.id)
    )
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is True

    other = await client.get(
        "/api/v1/auth/me", headers=auth_header(seeded_world.school_admin_a1.id)
    )
    assert other.status_code == 200
    assert other.json()["must_change_password"] is False


async def test_list_audit_logs_defaults_to_current_school(
    seeded_world, client, migrator_session
):
    ids = await _seed_audit_logs(migrator_session, seeded_world)

    resp = await client.get(
        "/api/v1/audit-logs",
        headers=auth_header(seeded_world.school_admin_a1.id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [row["id"] for row in body["items"]] == [ids["a1"]]
    assert body["has_more"] is False


async def test_list_audit_logs_respects_school_filter(
    seeded_world, client, migrator_session
):
    ids = await _seed_audit_logs(migrator_session, seeded_world)

    own = await client.get(
        "/api/v1/audit-logs",
        params={"school_id": seeded_world.school_a1_id},
        headers=auth_header(seeded_world.school_admin_a1.id),
    )
    assert own.status_code == 200
    assert [row["id"] for row in own.json()["items"]] == [ids["a1"]]

    # A school the principal cannot see returns an empty page, not a leak.
    foreign = await client.get(
        "/api/v1/audit-logs",
        params={"school_id": seeded_world.school_a2_id},
        headers=auth_header(seeded_world.school_admin_a1.id),
    )
    assert foreign.status_code == 200
    assert foreign.json()["items"] == []


async def test_list_audit_logs_supports_filters(
    seeded_world, client, migrator_session
):
    await _seed_audit_logs(migrator_session, seeded_world)
    async with migrator_session.begin():
        migrator_session.add(
            _audit_row(
                seeded_world.org_a_id,
                seeded_world.school_a1_id,
                actor_user_id=seeded_world.admin_a.id,
                action="USER_UPDATED",
                entity_type="user",
                summary="Changed a user",
            )
        )

    resp = await client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "user"},
        headers=auth_header(seeded_world.school_admin_a1.id),
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["action"] == "USER_UPDATED"
    assert items[0]["entity_type"] == "user"


async def test_org_admin_scopes_to_current_school(
    seeded_world, client, migrator_session
):
    ids = await _seed_audit_logs(migrator_session, seeded_world)

    resp = await client.get(
        "/api/v1/audit-logs",
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 200
    assert [row["id"] for row in resp.json()["items"]] == [ids["a1"]]


async def test_get_audit_log_scoped(seeded_world, client, migrator_session):
    ids = await _seed_audit_logs(migrator_session, seeded_world)

    own = await client.get(
        f"/api/v1/audit-logs/{ids['a1']}",
        headers=auth_header(seeded_world.school_admin_a1.id),
    )
    assert own.status_code == 200
    assert own.json()["action"] == "SCHOOL_UPDATED"

    foreign = await client.get(
        f"/api/v1/audit-logs/{ids['b1']}",
        headers=auth_header(seeded_world.school_admin_a1.id),
    )
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "AUDIT_LOG_NOT_FOUND"


async def test_audit_logs_require_permission(seeded_world, client, migrator_session):
    await _seed_audit_logs(migrator_session, seeded_world)

    resp = await client.get(
        "/api/v1/audit-logs",
        headers=auth_header(seeded_world.teacher_a1.id),
    )
    assert resp.status_code == 403

    read = await client.get(
        "/api/v1/audit-logs/does-not-exist",
        headers=auth_header(seeded_world.teacher_a1.id),
    )
    assert read.status_code == 403
