"""Enrollment module integration tests."""
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
        json={"first_name": first_name, "last_name": "Learner"},
        headers=auth(user_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_student(client, user_id: str, school_id: str, person_id: str, admission_number: str = "ADM-E001") -> dict:
    resp = await client.post(
        "/api/v1/students",
        json={
            "person_id": person_id,
            "admission_number": admission_number,
            "admission_date": "2024-01-15",
        },
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_academic_year(client, user_id: str, school_id: str, code: str = "2024-25") -> dict:
    resp = await client.post(
        "/api/v1/academic-years",
        json={
            "code": code,
            "name": f"Academic Year {code}",
            "start_date": "2024-04-01",
            "end_date": "2025-03-31",
        },
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_class(client, user_id: str, school_id: str, code: str = "CLS-1") -> dict:
    resp = await client.post(
        "/api/v1/academic-classes",
        json={"code": code, "name": f"Class {code}", "level": 1},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_cohort(client, user_id: str, school_id: str, academic_year_id: str, academic_class_id: str, name: str = "Section A") -> dict:
    resp = await client.post(
        "/api/v1/cohorts",
        json={
            "name": name,
            "academic_year_id": academic_year_id,
            "academic_class_id": academic_class_id,
        },
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_enrollment(
    client,
    user_id: str,
    school_id: str,
    student_id: str,
    academic_year_id: str,
    academic_class_id: str,
    cohort_id: str,
    roll_number: str | None = None,
    start_date: str = "2024-04-01",
) -> dict:
    payload = {
        "student_id": student_id,
        "academic_year_id": academic_year_id,
        "academic_class_id": academic_class_id,
        "cohort_id": cohort_id,
        "start_date": start_date,
    }
    if roll_number:
        payload["roll_number"] = roll_number
    resp = await client.post(
        "/api/v1/enrollments",
        json=payload,
        headers=school_auth(user_id, school_id),
    )
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_create_enrollment(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")
    student = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls = await _create_class(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], cls["id"])

    resp = await _create_enrollment(
        client,
        seeded_world.school_admin_a1.id,
        seeded_world.school_a1_id,
        student["id"],
        year["id"],
        cls["id"],
        cohort["id"],
        roll_number="R001",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["student_id"] == student["id"]
    assert body["status"] == "ACTIVE"
    assert body["enrollment_type"] == "REGULAR"
    assert body["roll_number"] == "R001"
    assert body["version"] == 1


async def test_get_enrollment(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    student = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls = await _create_class(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], cls["id"])

    create_resp = await _create_enrollment(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], year["id"], cls["id"], cohort["id"],
    )
    enrollment_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/enrollments/{enrollment_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == enrollment_id


async def test_update_enrollment_roll_number(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    student = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls = await _create_class(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], cls["id"])

    create_resp = await _create_enrollment(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], year["id"], cls["id"], cohort["id"],
    )
    body = create_resp.json()

    resp = await client.patch(
        f"/api/v1/enrollments/{body['id']}",
        json={"roll_number": "R999", "version": body["version"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["roll_number"] == "R999"
    assert resp.json()["version"] == 2


async def test_duplicate_active_enrollment_same_student_year(seeded_world, client):
    """Creating a second ACTIVE enrollment for the same student+year returns 409 ALREADY_ENROLLED."""
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    student = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls = await _create_class(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], cls["id"])

    resp1 = await _create_enrollment(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], year["id"], cls["id"], cohort["id"],
    )
    assert resp1.status_code == 201

    resp2 = await _create_enrollment(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], year["id"], cls["id"], cohort["id"],
    )
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "ALREADY_ENROLLED"


async def test_transfer_enrollment(seeded_world, client):
    """Transfer: old enrollment becomes TRANSFERRED, new enrollment is ACTIVE with TRANSFER_IN type."""
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    student = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls = await _create_class(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, "CLS-1")
    cls2 = await _create_class(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, "CLS-2")
    cohort_a = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], cls["id"], "Section A")
    cohort_b = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], cls2["id"], "Section B")

    create_resp = await _create_enrollment(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], year["id"], cls["id"], cohort_a["id"],
    )
    enrollment_id = create_resp.json()["id"]

    transfer_resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/transfer",
        json={
            "new_cohort_id": cohort_b["id"],
            "new_academic_class_id": cls2["id"],
            "effective_date": "2024-06-01",
            "reason": "Family relocation",
        },
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert transfer_resp.status_code == 201
    new_enrollment = transfer_resp.json()
    assert new_enrollment["status"] == "ACTIVE"
    assert new_enrollment["enrollment_type"] == "TRANSFER_IN"
    assert new_enrollment["cohort_id"] == cohort_b["id"]

    # Old enrollment should now be TRANSFERRED
    old_resp = await client.get(
        f"/api/v1/enrollments/{enrollment_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert old_resp.status_code == 200
    assert old_resp.json()["status"] == "TRANSFERRED"


async def test_enrollment_cross_tenant_isolation(seeded_world, client):
    """Enrollment created in school A1 is not visible to school B1 user."""
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    student = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls = await _create_class(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], cls["id"])

    create_resp = await _create_enrollment(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], year["id"], cls["id"], cohort["id"],
    )
    enrollment_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/enrollments/{enrollment_id}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404
