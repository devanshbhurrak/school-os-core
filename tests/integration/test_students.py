"""Students module integration tests."""
from __future__ import annotations

from app.core.security import create_access_token


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def school_auth(user_id: str, school_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id)}",
        "X-School-ID": school_id,
    }


async def _create_person(client, user_id: str, first_name: str = "Test") -> dict:
    resp = await client.post(
        "/api/v1/persons",
        json={"first_name": first_name, "last_name": "Student"},
        headers=auth(user_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_student(client, user_id: str, school_id: str, person_id: str, admission_number: str = "ADM-001") -> dict:
    resp = await client.post(
        "/api/v1/students",
        json={
            "person_id": person_id,
            "admission_number": admission_number,
            "admission_date": "2024-01-15",
        },
        headers=school_auth(user_id, school_id),
    )
    return resp


async def test_create_student(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")
    resp = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    assert resp.status_code == 201
    body = resp.json()
    assert body["admission_number"] == "ADM-001"
    assert body["school_id"] == seeded_world.school_a1_id
    assert body["person_id"] == person["id"]
    assert body["status"] == "ACTIVE"
    assert body["version"] == 1
    assert body["person_first_name"] == "Alice"


async def test_create_student_duplicate_admission_number(seeded_world, client):
    person1 = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")
    person2 = await _create_person(client, seeded_world.school_admin_a1.id, "Bob")

    resp1 = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person1["id"], "ADM-DUP")
    assert resp1.status_code == 201

    resp2 = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person2["id"], "ADM-DUP")
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "ADMISSION_NUMBER_TAKEN"


async def test_create_student_duplicate_person(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")

    resp1 = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"], "ADM-001")
    assert resp1.status_code == 201

    resp2 = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"], "ADM-002")
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "PERSON_ALREADY_ENROLLED"


async def test_get_student(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    create_resp = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    student_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/students/{student_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == student_id


async def test_update_student(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    create_resp = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    body = create_resp.json()

    resp = await client.patch(
        f"/api/v1/students/{body['id']}",
        json={"admission_number": "ADM-UPDATED", "version": body["version"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["admission_number"] == "ADM-UPDATED"
    assert resp.json()["version"] == 2


async def test_update_student_stale_version(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    create_resp = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    body = create_resp.json()

    resp = await client.patch(
        f"/api/v1/students/{body['id']}",
        json={"admission_number": "ADM-STALE", "version": 999},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 409


async def test_delete_student(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    create_resp = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    body = create_resp.json()

    del_resp = await client.request(
        "DELETE",
        f"/api/v1/students/{body['id']}",
        json={"version": body["version"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/students/{body['id']}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert get_resp.status_code == 404


async def test_list_students(seeded_world, client):
    person1 = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")
    person2 = await _create_person(client, seeded_world.school_admin_a1.id, "Bob")

    await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person1["id"], "ADM-001")
    await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person2["id"], "ADM-002")

    resp = await client.get(
        "/api/v1/students",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2


async def test_student_cross_tenant_isolation(seeded_world, client):
    """Student created in school A1 is not visible to school B1 user."""
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Isolated")
    create_resp = await _create_student(client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"])
    student_id = create_resp.json()["id"]

    # School B1 admin should NOT see this student
    resp = await client.get(
        f"/api/v1/students/{student_id}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404
