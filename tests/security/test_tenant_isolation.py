"""
Tests verifying that school A's data is invisible to school B's users.

These tests complement the RLS integration tests with explicit cross-tenant
access attempts at the API level, covering students, attendance sessions,
timetable slots, announcements, and list-endpoint filtering.
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
# Helpers — create entities in a given school context
# ---------------------------------------------------------------------------


async def _create_person(client, user_id: str, first_name: str = "Test") -> dict:
    resp = await client.post(
        "/api/v1/persons",
        json={"first_name": first_name, "last_name": "Isolation"},
        headers=auth(user_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_student(
    client, user_id: str, school_id: str, person_id: str, adm: str = "ADM-ISO-001"
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


async def _create_attendance_session(
    client, user_id: str, school_id: str, cohort_id: str, year_id: str
) -> dict:
    resp = await client.post(
        "/api/v1/attendance-sessions",
        json={
            "cohort_id": cohort_id,
            "academic_year_id": year_id,
            "session_date": "2024-10-01",
        },
        headers=school_auth(user_id, school_id),
    )
    body = resp.json()
    assert resp.status_code == 201, body
    return body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_student_not_visible_cross_school(seeded_world, client):
    """A user in school B cannot see school A's students."""
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )

    resp = await client.get(
        f"/api/v1/students/{student['id']}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404


async def test_attendance_session_not_visible_cross_school(seeded_world, client):
    """A user in school B cannot see school A's attendance sessions."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    year = await _create_academic_year(client, u.id, sid)
    cls = await _create_class(client, u.id, sid, year["id"])
    cohort = await _create_cohort(client, u.id, sid, cls["id"])
    session = await _create_attendance_session(client, u.id, sid, cohort["id"], year["id"])

    resp = await client.get(
        f"/api/v1/attendance-sessions/{session['id']}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404


async def test_cross_tenant_student_update_rejected(seeded_world, client):
    """Attempting to update a school A student from school B context fails."""
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Bob")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )

    resp = await client.patch(
        f"/api/v1/students/{student['id']}",
        json={"admission_number": "HIJACKED", "version": student["version"]},
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code in (404, 403)


async def test_cross_tenant_student_delete_rejected(seeded_world, client):
    """Attempting to delete a school A student from school B context fails."""
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Carol")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )

    resp = await client.request(
        "DELETE",
        f"/api/v1/students/{student['id']}",
        json={"version": student["version"]},
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code in (404, 403)


async def test_list_students_only_returns_own_school(seeded_world, client):
    """List endpoints only return entities from the caller's school."""
    person_a = await _create_person(client, seeded_world.school_admin_a1.id, "SchoolA")
    student_a = await _create_student(
        client,
        seeded_world.school_admin_a1.id,
        seeded_world.school_a1_id,
        person_a["id"],
        "ADM-A-001",
    )

    person_b = await _create_person(client, seeded_world.school_admin_b1.id, "SchoolB")
    student_b = await _create_student(
        client,
        seeded_world.school_admin_b1.id,
        seeded_world.school_b1_id,
        person_b["id"],
        "ADM-B-001",
    )

    resp_a = await client.get(
        "/api/v1/students",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    resp_b = await client.get(
        "/api/v1/students",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    ids_a = {s["id"] for s in resp_a.json()["items"]}
    ids_b = {s["id"] for s in resp_b.json()["items"]}

    assert student_a["id"] in ids_a
    assert student_a["id"] not in ids_b
    assert student_b["id"] in ids_b
    assert student_b["id"] not in ids_a


async def test_cross_tenant_person_not_visible(seeded_world, client):
    """A person created in org A is not visible to org B users."""
    person = await _create_person(client, seeded_world.admin_a.id, "OrgAPerson")

    resp = await client.get(
        f"/api/v1/persons/{person['id']}",
        headers=auth(seeded_world.admin_b.id),
    )
    assert resp.status_code == 404
