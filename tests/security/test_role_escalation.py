"""Tests that lower-privileged roles cannot escalate to admin actions.

Each test authenticates as a TEACHER-role user and verifies that
admin-only operations are rejected with 403 FORBIDDEN.
"""
from __future__ import annotations

from app.core.security import create_access_token


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def school_auth(user_id: str, school_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id)}",
        "X-School-ID": school_id,
    }


# ---------------------------------------------------------------------------
# Student management — teacher should not create/delete students
# ---------------------------------------------------------------------------


async def test_teacher_cannot_create_student(seeded_world, client):
    """A teacher-role user cannot create students."""
    # First create a person (teachers may have person-read but we need a
    # person_id; use the admin to create one).
    person_resp = await client.post(
        "/api/v1/persons",
        json={"first_name": "Blocked", "last_name": "Student"},
        headers=auth(seeded_world.school_admin_a1.id),
    )
    assert person_resp.status_code == 201
    person_id = person_resp.json()["id"]

    resp = await client.post(
        "/api/v1/students",
        json={
            "person_id": person_id,
            "admission_number": "ADM-TEACHER-001",
            "admission_date": "2024-01-15",
        },
        headers=school_auth(seeded_world.teacher_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 403


async def test_teacher_cannot_delete_student(seeded_world, client):
    """A teacher-role user cannot delete students."""
    # Create student as admin
    person_resp = await client.post(
        "/api/v1/persons",
        json={"first_name": "ToDelete", "last_name": "Student"},
        headers=auth(seeded_world.school_admin_a1.id),
    )
    student_resp = await client.post(
        "/api/v1/students",
        json={
            "person_id": person_resp.json()["id"],
            "admission_number": "ADM-DEL-001",
            "admission_date": "2024-01-15",
        },
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert student_resp.status_code == 201
    student = student_resp.json()

    resp = await client.request(
        "DELETE",
        f"/api/v1/students/{student['id']}",
        json={"version": student["version"]},
        headers=school_auth(seeded_world.teacher_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Audit logs — teachers should not access
# ---------------------------------------------------------------------------


async def test_teacher_cannot_access_audit_logs(seeded_world, client):
    """Teachers cannot access audit logs."""
    resp = await client.get(
        "/api/v1/audit-logs",
        headers=auth(seeded_world.teacher_a1.id),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# User management — teachers should not create users
# ---------------------------------------------------------------------------


async def test_teacher_cannot_create_user(seeded_world, client):
    """Teachers cannot create users."""
    resp = await client.post(
        "/api/v1/users",
        json={"email": "rogue@test.local", "password": "RoguePass2026!"},
        headers=auth(seeded_world.teacher_a1.id),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Organization management — teachers should not access
# ---------------------------------------------------------------------------


async def test_teacher_cannot_create_organization(seeded_world, client):
    """Teachers cannot create organizations."""
    resp = await client.post(
        "/api/v1/organizations",
        json={"code": "rogue-org", "name": "Rogue Org"},
        headers=auth(seeded_world.teacher_a1.id),
    )
    assert resp.status_code == 403


async def test_teacher_cannot_create_school(seeded_world, client):
    """Teachers cannot create schools."""
    resp = await client.post(
        "/api/v1/schools",
        json={"code": "rogue-sch", "name": "Rogue School"},
        headers=auth(seeded_world.teacher_a1.id),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Membership / role management — teachers should not manage
# ---------------------------------------------------------------------------


async def test_teacher_cannot_create_membership(seeded_world, client):
    """Teachers cannot assign memberships."""
    resp = await client.post(
        "/api/v1/memberships",
        json={
            "user_id": seeded_world.lone_user.id,
            "school_id": seeded_world.school_a1_id,
            "role_ids": [],
        },
        headers=auth(seeded_world.teacher_a1.id),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# School admin cannot do platform-admin-level actions
# ---------------------------------------------------------------------------


async def test_school_admin_cannot_create_organization(seeded_world, client):
    """School admins cannot create organizations (platform admin only)."""
    resp = await client.post(
        "/api/v1/organizations",
        json={"code": "escalated", "name": "Escalated Org"},
        headers=auth(seeded_world.school_admin_a1.id),
    )
    assert resp.status_code == 403
