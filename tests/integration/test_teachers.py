"""Teachers module integration tests."""
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
        json={"first_name": first_name, "last_name": "Teacher"},
        headers=auth(user_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_teacher(
    client,
    user_id: str,
    school_id: str,
    person_id: str,
    employee_number: str = "EMP-001",
) -> dict:
    resp = await client.post(
        "/api/v1/teachers",
        json={
            "person_id": person_id,
            "employee_number": employee_number,
            "designation": "Teacher",
            "joining_date": "2024-01-15",
        },
        headers=school_auth(user_id, school_id),
    )
    return resp


async def test_create_teacher(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")
    resp = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["employee_number"] == "EMP-001"
    assert body["school_id"] == seeded_world.school_a1_id
    assert body["person_id"] == person["id"]
    assert body["status"] == "ACTIVE"
    assert body["version"] == 1


async def test_create_teacher_duplicate_person(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Bob")

    resp1 = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"], "EMP-001"
    )
    assert resp1.status_code == 201

    resp2 = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"], "EMP-002"
    )
    assert resp2.status_code == 409


async def test_create_teacher_duplicate_employee_number(seeded_world, client):
    person1 = await _create_person(client, seeded_world.school_admin_a1.id, "Alice")
    person2 = await _create_person(client, seeded_world.school_admin_a1.id, "Bob")

    resp1 = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person1["id"], "EMP-DUP"
    )
    assert resp1.status_code == 201

    resp2 = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person2["id"], "EMP-DUP"
    )
    assert resp2.status_code == 409


async def test_get_teacher(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    create_resp = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )
    teacher_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/teachers/{teacher_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == teacher_id


async def test_update_teacher(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    create_resp = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )
    body = create_resp.json()

    resp = await client.patch(
        f"/api/v1/teachers/{body['id']}",
        json={"designation": "Senior Teacher", "version": body["version"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["designation"] == "Senior Teacher"
    assert resp.json()["version"] == 2


async def test_update_teacher_stale_version(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    create_resp = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )
    body = create_resp.json()

    resp = await client.patch(
        f"/api/v1/teachers/{body['id']}",
        json={"designation": "Stale", "version": 999},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 409


async def test_delete_teacher(seeded_world, client):
    person = await _create_person(client, seeded_world.school_admin_a1.id)
    create_resp = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )
    body = create_resp.json()

    del_resp = await client.request(
        "DELETE",
        f"/api/v1/teachers/{body['id']}",
        json={"version": body["version"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/teachers/{body['id']}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert get_resp.status_code == 404


async def test_teacher_cross_tenant_isolation(seeded_world, client):
    """Teacher created in school A1 is not visible to school B1 user."""
    person = await _create_person(client, seeded_world.school_admin_a1.id, "Isolated")
    create_resp = await _create_teacher(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, person["id"]
    )
    teacher_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/teachers/{teacher_id}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404
