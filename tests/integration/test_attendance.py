"""Attendance module integration tests."""
from __future__ import annotations

from datetime import date

import pytest

from app.core.security import create_access_token
from app.db.types import gen_ulid


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


async def _create_academic_year(client, user_id: str, school_id: str, code: str = "2024-2025") -> dict:
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


async def _create_class(client, user_id: str, school_id: str, year_id: str, code: str = "GR1") -> dict:
    resp = await client.post(
        "/api/v1/academic-classes",
        json={"code": code, "name": f"Grade {code}", "academic_year_id": year_id},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_cohort(client, user_id: str, school_id: str, class_id: str, code: str = "SEC-A") -> dict:
    resp = await client.post(
        "/api/v1/cohorts",
        json={"code": code, "name": f"Section {code}", "academic_class_id": class_id},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_person(client, user_id: str, first_name: str = "Test") -> dict:
    resp = await client.post(
        "/api/v1/persons",
        json={"first_name": first_name, "last_name": "Student"},
        headers=auth(user_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_student(client, user_id: str, school_id: str, person_id: str, adm: str = "ADM-001") -> dict:
    resp = await client.post(
        "/api/v1/students",
        json={"person_id": person_id, "admission_number": adm, "admission_date": "2024-01-01"},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_enrollment(
    client, user_id: str, school_id: str, student_id: str,
    academic_year_id: str, academic_class_id: str, cohort_id: str
) -> dict:
    resp = await client.post(
        "/api/v1/enrollments",
        json={
            "student_id": student_id,
            "academic_year_id": academic_year_id,
            "academic_class_id": academic_class_id,
            "cohort_id": cohort_id,
            "start_date": "2024-09-01",
        },
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_session(client, user_id: str, school_id: str, cohort_id: str, year_id: str, session_date: str = "2024-10-01") -> dict:
    resp = await client.post(
        "/api/v1/attendance-sessions",
        json={
            "cohort_id": cohort_id,
            "academic_year_id": year_id,
            "session_date": session_date,
        },
        headers=school_auth(user_id, school_id),
    )
    return resp.json(), resp.status_code


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_create_session_auto_creates_records(seeded_world, client):
    """Creating a session auto-populates records for enrolled students."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    year = await _create_academic_year(client, u.id, sid)
    cls = await _create_class(client, u.id, sid, year["id"])
    cohort = await _create_cohort(client, u.id, sid, cls["id"])

    person = await _create_person(client, u.id, "Alice")
    student = await _create_student(client, u.id, sid, person["id"])
    await _create_enrollment(client, u.id, sid, student["id"], year["id"], cls["id"], cohort["id"])

    body, status_code = await _create_session(client, u.id, sid, cohort["id"], year["id"])
    assert status_code == 201, body
    assert body["status"] == "DRAFT"
    assert body["record_count"] >= 1

    records_resp = await client.get(
        f"/api/v1/attendance-sessions/{body['id']}/records",
        headers=school_auth(u.id, sid),
    )
    assert records_resp.status_code == 200
    records = records_resp.json()
    assert len(records) >= 1
    assert all(r["status"] == "PRESENT" for r in records)


async def test_submit_session(seeded_world, client):
    """Submitting a DRAFT session changes status to SUBMITTED."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    year = await _create_academic_year(client, u.id, sid)
    cls = await _create_class(client, u.id, sid, year["id"])
    cohort = await _create_cohort(client, u.id, sid, cls["id"])

    body, _ = await _create_session(client, u.id, sid, cohort["id"], year["id"])
    session_id = body["id"]
    version = body["version"]

    resp = await client.post(
        f"/api/v1/attendance-sessions/{session_id}/submit",
        json={"version": version},
        headers=school_auth(u.id, sid),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUBMITTED"
    assert resp.json()["submitted_at"] is not None


async def test_update_record_while_draft(seeded_world, client):
    """Updating a record in a DRAFT session succeeds."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    year = await _create_academic_year(client, u.id, sid)
    cls = await _create_class(client, u.id, sid, year["id"])
    cohort = await _create_cohort(client, u.id, sid, cls["id"])

    person = await _create_person(client, u.id, "Bob")
    student = await _create_student(client, u.id, sid, person["id"])
    await _create_enrollment(client, u.id, sid, student["id"], year["id"], cls["id"], cohort["id"])

    body, _ = await _create_session(client, u.id, sid, cohort["id"], year["id"])
    session_id = body["id"]

    records_resp = await client.get(
        f"/api/v1/attendance-sessions/{session_id}/records",
        headers=school_auth(u.id, sid),
    )
    record_id = records_resp.json()[0]["id"]

    resp = await client.patch(
        f"/api/v1/attendance-records/{record_id}",
        json={"status": "ABSENT"},
        headers=school_auth(u.id, sid),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ABSENT"


async def test_update_record_while_submitted_is_forbidden(seeded_world, client):
    """Updating a record in a SUBMITTED session returns 403."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    year = await _create_academic_year(client, u.id, sid)
    cls = await _create_class(client, u.id, sid, year["id"])
    cohort = await _create_cohort(client, u.id, sid, cls["id"])

    person = await _create_person(client, u.id, "Carol")
    student = await _create_student(client, u.id, sid, person["id"])
    await _create_enrollment(client, u.id, sid, student["id"], year["id"], cls["id"], cohort["id"])

    body, _ = await _create_session(client, u.id, sid, cohort["id"], year["id"])
    session_id = body["id"]
    version = body["version"]

    await client.post(
        f"/api/v1/attendance-sessions/{session_id}/submit",
        json={"version": version},
        headers=school_auth(u.id, sid),
    )

    records_resp = await client.get(
        f"/api/v1/attendance-sessions/{session_id}/records",
        headers=school_auth(u.id, sid),
    )
    record_id = records_resp.json()[0]["id"]

    resp = await client.patch(
        f"/api/v1/attendance-records/{record_id}",
        json={"status": "LATE"},
        headers=school_auth(u.id, sid),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "SESSION_SUBMITTED"


async def test_amend_session_then_update_record(seeded_world, client):
    """Amending a SUBMITTED session allows record updates again."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    year = await _create_academic_year(client, u.id, sid)
    cls = await _create_class(client, u.id, sid, year["id"])
    cohort = await _create_cohort(client, u.id, sid, cls["id"])

    person = await _create_person(client, u.id, "Dave")
    student = await _create_student(client, u.id, sid, person["id"])
    await _create_enrollment(client, u.id, sid, student["id"], year["id"], cls["id"], cohort["id"])

    body, _ = await _create_session(client, u.id, sid, cohort["id"], year["id"])
    session_id = body["id"]

    submit_resp = await client.post(
        f"/api/v1/attendance-sessions/{session_id}/submit",
        json={"version": body["version"]},
        headers=school_auth(u.id, sid),
    )
    assert submit_resp.status_code == 200
    submitted_version = submit_resp.json()["version"]

    amend_resp = await client.post(
        f"/api/v1/attendance-sessions/{session_id}/amend",
        json={"version": submitted_version},
        headers=school_auth(u.id, sid),
    )
    assert amend_resp.status_code == 200
    assert amend_resp.json()["status"] == "AMENDED"

    records_resp = await client.get(
        f"/api/v1/attendance-sessions/{session_id}/records",
        headers=school_auth(u.id, sid),
    )
    record_id = records_resp.json()[0]["id"]

    resp = await client.patch(
        f"/api/v1/attendance-records/{record_id}",
        json={"status": "EXCUSED"},
        headers=school_auth(u.id, sid),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "EXCUSED"


async def test_duplicate_session_same_cohort_date(seeded_world, client):
    """Creating two sessions for the same cohort+date returns 409."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    year = await _create_academic_year(client, u.id, sid)
    cls = await _create_class(client, u.id, sid, year["id"])
    cohort = await _create_cohort(client, u.id, sid, cls["id"])

    _, status1 = await _create_session(client, u.id, sid, cohort["id"], year["id"])
    assert status1 == 201

    body2, status2 = await _create_session(client, u.id, sid, cohort["id"], year["id"])
    assert status2 == 409
    assert body2["error"]["code"] == "SESSION_ALREADY_EXISTS"


async def test_cross_tenant_isolation(seeded_world, client):
    """Session created in school A1 is not visible to school B1 user."""
    u_a = seeded_world.school_admin_a1
    u_b = seeded_world.school_admin_b1
    sid_a = seeded_world.school_a1_id
    sid_b = seeded_world.school_b1_id

    year = await _create_academic_year(client, u_a.id, sid_a)
    cls = await _create_class(client, u_a.id, sid_a, year["id"])
    cohort = await _create_cohort(client, u_a.id, sid_a, cls["id"])

    body, _ = await _create_session(client, u_a.id, sid_a, cohort["id"], year["id"])
    session_id = body["id"]

    resp = await client.get(
        f"/api/v1/attendance-sessions/{session_id}",
        headers=school_auth(u_b.id, sid_b),
    )
    assert resp.status_code == 404
