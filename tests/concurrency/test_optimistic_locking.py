"""Tests for optimistic locking under concurrent access.

Verifies that stale-version writes are rejected with 409 (STALE_RESOURCE)
for students, persons, and attendance session submissions.
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
# Helpers
# ---------------------------------------------------------------------------


async def _create_person(client, user_id: str, first_name: str = "Test") -> dict:
    resp = await client.post(
        "/api/v1/persons",
        json={"first_name": first_name, "last_name": "Locking"},
        headers=auth(user_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_student(
    client, user_id: str, school_id: str, person_id: str, adm: str = "ADM-LOCK-001"
) -> dict:
    resp = await client.post(
        "/api/v1/students",
        json={"person_id": person_id, "admission_number": adm, "admission_date": "2024-01-15"},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_academic_year(
    client, user_id: str, school_id: str, code: str = "2024-2025"
) -> dict:
    resp = await client.post(
        "/api/v1/academic-years",
        json={
            "code": code,
            "name": f"Year {code}",
            "start_date": "2024-09-01",
            "end_date": "2025-07-31",
            "is_current": True,
        },
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_class(
    client, user_id: str, school_id: str, year_id: str, code: str = "GR1"
) -> dict:
    resp = await client.post(
        "/api/v1/academic-classes",
        json={"code": code, "name": f"Grade {code}", "academic_year_id": year_id},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_cohort(
    client, user_id: str, school_id: str, class_id: str, code: str = "SEC-A"
) -> dict:
    resp = await client.post(
        "/api/v1/cohorts",
        json={"code": code, "name": f"Section {code}", "academic_class_id": class_id},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_concurrent_person_update_version_mismatch(seeded_world, client):
    """Two updates to the same person with the same version: second gets 409."""
    person = await _create_person(client, seeded_world.admin_a.id, "Alice")
    v = person["version"]

    resp1 = await client.patch(
        f"/api/v1/persons/{person['id']}",
        json={"first_name": "Alice-V2", "version": v},
        headers=auth(seeded_world.admin_a.id),
    )
    assert resp1.status_code == 200

    resp2 = await client.patch(
        f"/api/v1/persons/{person['id']}",
        json={"first_name": "Alice-Stale", "version": v},
        headers=auth(seeded_world.admin_a.id),
    )
    assert resp2.status_code == 409


async def test_concurrent_student_update_version_mismatch(seeded_world, client):
    """Two updates to the same student with the same version: second gets 409."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    person = await _create_person(client, u.id, "Bob")
    student = await _create_student(client, u.id, sid, person["id"])
    v = student["version"]

    resp1 = await client.patch(
        f"/api/v1/students/{student['id']}",
        json={"admission_number": "ADM-V2", "version": v},
        headers=school_auth(u.id, sid),
    )
    assert resp1.status_code == 200

    resp2 = await client.patch(
        f"/api/v1/students/{student['id']}",
        json={"admission_number": "ADM-STALE", "version": v},
        headers=school_auth(u.id, sid),
    )
    assert resp2.status_code == 409


async def test_concurrent_attendance_submit_stale_error(seeded_world, client):
    """When an attendance session is submitted twice with the same version,
    the second attempt gets a stale resource error."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    year = await _create_academic_year(client, u.id, sid)
    cls = await _create_class(client, u.id, sid, year["id"])
    cohort = await _create_cohort(client, u.id, sid, cls["id"])

    session_resp = await client.post(
        "/api/v1/attendance-sessions",
        json={
            "cohort_id": cohort["id"],
            "academic_year_id": year["id"],
            "session_date": "2024-10-01",
        },
        headers=school_auth(u.id, sid),
    )
    body = session_resp.json()
    assert session_resp.status_code == 201, body
    session_id = body["id"]
    version = body["version"]

    # First submit succeeds
    resp1 = await client.post(
        f"/api/v1/attendance-sessions/{session_id}/submit",
        json={"version": version},
        headers=school_auth(u.id, sid),
    )
    assert resp1.status_code == 200

    # Second submit with same version fails (status already changed + version bumped)
    resp2 = await client.post(
        f"/api/v1/attendance-sessions/{session_id}/submit",
        json={"version": version},
        headers=school_auth(u.id, sid),
    )
    assert resp2.status_code == 409


async def test_delete_with_stale_version_rejected(seeded_world, client):
    """Deleting a student with a stale version is rejected."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    person = await _create_person(client, u.id, "StaleDelete")
    student = await _create_student(client, u.id, sid, person["id"], "ADM-SD-001")

    # Bump the version via an update
    resp = await client.patch(
        f"/api/v1/students/{student['id']}",
        json={"admission_number": "ADM-SD-002", "version": student["version"]},
        headers=school_auth(u.id, sid),
    )
    assert resp.status_code == 200

    # Delete with original (now stale) version
    del_resp = await client.request(
        "DELETE",
        f"/api/v1/students/{student['id']}",
        json={"version": student["version"]},
        headers=school_auth(u.id, sid),
    )
    assert del_resp.status_code == 409
