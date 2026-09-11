"""IAM flows: organization/school/user/membership creation and permission
boundaries (platform admin vs org admin vs school admin vs no-membership)."""
from __future__ import annotations

from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.iam.models import Role


def auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def test_platform_admin_creates_organization(seeded_world, client):
    resp = await client.post(
        "/api/v1/organizations",
        json={"code": "neworg", "name": "New Org"},
        headers=auth_header(seeded_world.platform_admin.id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["code"] == "neworg"


async def test_org_admin_creates_school_in_own_org(seeded_world, client):
    resp = await client.post(
        "/api/v1/schools",
        json={"code": "sch-new", "name": "School New"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["organization_id"] == seeded_world.org_a_id
    assert body["code"] == "sch-new"


async def test_org_admin_creates_user_and_membership_with_role(
    seeded_world, client, app_session
):
    create_user = await client.post(
        "/api/v1/users",
        json={"email": "fresh.user@acme-school.org", "password": "FreshUserPass2026!"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert create_user.status_code == 201
    user_id = create_user.json()["id"]

    teacher_role = await app_session.scalar(
        select(Role).where(Role.code == "TEACHER", Role.organization_id.is_(None))
    )
    membership = await client.post(
        "/api/v1/memberships",
        json={
            "user_id": user_id,
            "school_id": seeded_world.school_a2_id,
            "role_ids": [teacher_role.id],
        },
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert membership.status_code == 201
    body = membership.json()
    assert body["organization_id"] == seeded_world.org_a_id
    assert body["school_id"] == seeded_world.school_a2_id
    assert "TEACHER" in body["role_codes"]


async def test_school_admin_denied_organization_routes(seeded_world, client):
    resp = await client.get(
        "/api/v1/organizations", headers=auth_header(seeded_world.school_admin_a1.id)
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


async def test_lone_user_has_no_permissions(seeded_world, client):
    resp = await client.get("/api/v1/schools", headers=auth_header(seeded_world.lone_user.id))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


async def test_org_b_admin_cannot_read_org_a_data(seeded_world, client):
    resp = await client.get(
        f"/api/v1/schools/{seeded_world.school_a1_id}",
        headers=auth_header(seeded_world.admin_b.id),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SCHOOL_NOT_FOUND"
