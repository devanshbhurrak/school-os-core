"""Timetables module integration tests."""
from __future__ import annotations

from app.core.security import create_access_token


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def school_auth(user_id: str, school_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id)}",
        "X-School-ID": school_id,
    }


async def _create_academic_year(client, user_id: str, school_id: str, code: str = "2024-25") -> dict:
    resp = await client.post(
        "/api/v1/academic-years",
        json={"code": code, "name": f"Year {code}", "start_date": "2024-09-01", "end_date": "2025-07-31"},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_cohort(client, user_id: str, school_id: str, academic_year_id: str, name: str = "10A") -> dict:
    # First create an academic class
    cls_resp = await client.post(
        "/api/v1/academic-classes",
        json={"name": "Grade 10", "code": "G10"},
        headers=school_auth(user_id, school_id),
    )
    assert cls_resp.status_code == 201
    cls_id = cls_resp.json()["id"]

    resp = await client.post(
        "/api/v1/cohorts",
        json={"name": name, "academic_class_id": cls_id, "academic_year_id": academic_year_id},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_subject(client, user_id: str, school_id: str, code: str = "MATH") -> dict:
    resp = await client.post(
        "/api/v1/subjects",
        json={"code": code, "name": f"Subject {code}"},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_person(client, user_id: str, first_name: str = "Test") -> dict:
    resp = await client.post(
        "/api/v1/persons",
        json={"first_name": first_name, "last_name": "Teacher"},
        headers=auth(user_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_teacher(client, user_id: str, school_id: str, person_id: str, emp: str = "EMP-T01") -> dict:
    resp = await client.post(
        "/api/v1/teachers",
        json={"person_id": person_id, "employee_number": emp},
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_period(
    client, user_id: str, school_id: str, academic_year_id: str,
    name: str = "Period 1", start: str = "08:00:00", end: str = "09:00:00", sort_order: int = 0,
) -> dict:
    resp = await client.post(
        "/api/v1/period-definitions",
        json={
            "academic_year_id": academic_year_id,
            "name": name,
            "period_type": "LESSON",
            "start_time": start,
            "end_time": end,
            "sort_order": sort_order,
        },
        headers=school_auth(user_id, school_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_slot(
    client, user_id: str, school_id: str,
    cohort_id: str, period_definition_id: str, teacher_id: str, subject_id: str,
    day_of_week: str = "MONDAY", effective_from: str = "2024-09-01",
) -> dict:
    resp = await client.post(
        "/api/v1/timetable-slots",
        json={
            "cohort_id": cohort_id,
            "period_definition_id": period_definition_id,
            "teacher_id": teacher_id,
            "subject_id": subject_id,
            "day_of_week": day_of_week,
            "effective_from": effective_from,
        },
        headers=school_auth(user_id, school_id),
    )
    return resp


async def test_create_period_definition(seeded_world, client):
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    resp = await _create_period(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"]
    )
    assert resp["name"] == "Period 1"
    assert resp["period_type"] == "LESSON"
    assert resp["school_id"] == seeded_world.school_a1_id


async def test_list_period_definitions(seeded_world, client):
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    await _create_period(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], "Period 1", sort_order=0)
    await _create_period(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"], "Period 2", start="09:00:00", end="10:00:00", sort_order=1)

    resp = await client.get(
        f"/api/v1/period-definitions?academic_year_id={year['id']}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


async def test_create_timetable_slot(seeded_world, client):
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])
    subject = await _create_subject(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    teacher = await _create_teacher(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    period = await _create_period(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])

    resp = await _create_slot(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        cohort["id"], period["id"], teacher["id"], subject["id"],
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["cohort_id"] == cohort["id"]
    assert body["teacher_id"] == teacher["id"]
    assert body["status"] == "ACTIVE"
    assert body["version"] == 1


async def test_teacher_conflict_detection(seeded_world, client):
    """Creating two slots for the same teacher, same period, same day → 409 TEACHER_CONFLICT."""
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    subject = await _create_subject(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    teacher = await _create_teacher(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    period = await _create_period(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])

    # Create two cohorts
    cls_resp = await client.post(
        "/api/v1/academic-classes",
        json={"name": "Grade 10", "code": "G10"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert cls_resp.status_code == 201
    cls_id = cls_resp.json()["id"]

    cohort1_resp = await client.post(
        "/api/v1/cohorts",
        json={"name": "10A", "academic_class_id": cls_id, "academic_year_id": year["id"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    cohort2_resp = await client.post(
        "/api/v1/cohorts",
        json={"name": "10B", "academic_class_id": cls_id, "academic_year_id": year["id"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert cohort1_resp.status_code == 201
    assert cohort2_resp.status_code == 201
    cohort1_id = cohort1_resp.json()["id"]
    cohort2_id = cohort2_resp.json()["id"]

    # First slot OK
    resp1 = await _create_slot(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        cohort1_id, period["id"], teacher["id"], subject["id"],
    )
    assert resp1.status_code == 201

    # Second slot: same teacher, same period, same day → conflict
    resp2 = await client.post(
        "/api/v1/timetable-slots",
        json={
            "cohort_id": cohort2_id,
            "period_definition_id": period["id"],
            "teacher_id": teacher["id"],
            "subject_id": subject["id"],
            "day_of_week": "MONDAY",
            "effective_from": "2024-09-01",
        },
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "TEACHER_CONFLICT"


async def test_cohort_conflict_detection(seeded_world, client):
    """Creating two slots for the same cohort, same period, same day → 409 COHORT_CONFLICT."""
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])
    subject = await _create_subject(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    period = await _create_period(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])

    # Two different teachers
    person1 = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")
    person2 = await _create_person(client, seeded_world.school_admin_a1.id, "Bob")
    teacher1 = await _create_teacher(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person1["id"], "EMP-A")
    teacher2 = await _create_teacher(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person2["id"], "EMP-B")

    resp1 = await _create_slot(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        cohort["id"], period["id"], teacher1["id"], subject["id"],
    )
    assert resp1.status_code == 201

    # Same cohort, same period, same day → COHORT_CONFLICT
    resp2 = await client.post(
        "/api/v1/timetable-slots",
        json={
            "cohort_id": cohort["id"],
            "period_definition_id": period["id"],
            "teacher_id": teacher2["id"],
            "subject_id": subject["id"],
            "day_of_week": "MONDAY",
            "effective_from": "2024-09-01",
        },
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "COHORT_CONFLICT"


async def test_update_slot(seeded_world, client):
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])
    subject = await _create_subject(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    teacher = await _create_teacher(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    period = await _create_period(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])

    slot_resp = await _create_slot(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        cohort["id"], period["id"], teacher["id"], subject["id"],
    )
    slot = slot_resp.json()

    resp = await client.patch(
        f"/api/v1/timetable-slots/{slot['id']}",
        json={"notes": "Updated notes", "version": slot["version"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated notes"
    assert resp.json()["version"] == 2


async def test_cancel_slot(seeded_world, client):
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cohort = await _create_cohort(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])
    subject = await _create_subject(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    teacher = await _create_teacher(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    period = await _create_period(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])

    slot_resp = await _create_slot(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        cohort["id"], period["id"], teacher["id"], subject["id"],
    )
    slot = slot_resp.json()

    resp = await client.delete(
        f"/api/v1/timetable-slots/{slot['id']}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "CANCELLED"
    assert body["effective_to"] is not None


async def test_timetable_cross_tenant_isolation(seeded_world, client):
    """Period created in school A1 is not visible to school B1 user."""
    year = await _create_academic_year(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    period = await _create_period(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, year["id"])

    resp = await client.get(
        f"/api/v1/period-definitions/{period['id']}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404
