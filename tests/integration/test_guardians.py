"""Student guardians integration tests."""
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
        json={"first_name": first_name, "last_name": "Person"},
        headers=auth(user_id),
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_student(
    client, user_id: str, school_id: str, person_id: str, admission_number: str = "ADM-G001"
) -> dict:
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


async def _add_guardian(
    client,
    user_id: str,
    school_id: str,
    student_id: str,
    guardian_person_id: str,
    relationship: str = "FATHER",
    is_primary: bool = False,
) -> dict:
    resp = await client.post(
        "/api/v1/student-guardians",
        json={
            "student_id": student_id,
            "guardian_person_id": guardian_person_id,
            "relationship": relationship,
            "is_primary": is_primary,
        },
        headers=school_auth(user_id, school_id),
    )
    return resp


async def test_add_guardian(seeded_world, client):
    student_person = await _create_person(client, seeded_world.school_admin_a1.id, "StudentA")
    guardian_person = await _create_person(client, seeded_world.school_admin_a1.id, "GuardianA")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, student_person["id"]
    )

    resp = await _add_guardian(
        client,
        seeded_world.school_admin_a1.id,
        seeded_world.school_a1_id,
        student["id"],
        guardian_person["id"],
        relationship="FATHER",
        is_primary=True,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["student_id"] == student["id"]
    assert body["guardian_person_id"] == guardian_person["id"]
    assert body["relationship"] == "FATHER"
    assert body["is_primary"] is True
    assert body["guardian_first_name"] == "GuardianA"


async def test_list_guardians_for_student(seeded_world, client):
    student_person = await _create_person(client, seeded_world.school_admin_a1.id, "StudentB")
    guardian1 = await _create_person(client, seeded_world.school_admin_a1.id, "Guardian1")
    guardian2 = await _create_person(client, seeded_world.school_admin_a1.id, "Guardian2")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student_person["id"], "ADM-G002"
    )

    await _add_guardian(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], guardian1["id"], "MOTHER", True
    )
    await _add_guardian(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], guardian2["id"], "FATHER", False
    )

    resp = await client.get(
        f"/api/v1/students/{student['id']}/guardians",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    # Primary guardian should come first
    assert items[0]["is_primary"] is True


async def test_duplicate_guardian_link_returns_409(seeded_world, client):
    student_person = await _create_person(client, seeded_world.school_admin_a1.id, "StudentC")
    guardian_person = await _create_person(client, seeded_world.school_admin_a1.id, "GuardianC")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student_person["id"], "ADM-G003"
    )

    resp1 = await _add_guardian(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], guardian_person["id"]
    )
    assert resp1.status_code == 201

    resp2 = await _add_guardian(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], guardian_person["id"]
    )
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "GUARDIAN_ALREADY_LINKED"


async def test_primary_guardian_auto_unset_on_new_primary(seeded_world, client):
    student_person = await _create_person(client, seeded_world.school_admin_a1.id, "StudentD")
    guardian1 = await _create_person(client, seeded_world.school_admin_a1.id, "GuardianD1")
    guardian2 = await _create_person(client, seeded_world.school_admin_a1.id, "GuardianD2")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student_person["id"], "ADM-G004"
    )

    resp1 = await _add_guardian(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], guardian1["id"], "MOTHER", True
    )
    g1_id = resp1.json()["id"]

    # Add a second primary — should unset first
    await _add_guardian(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], guardian2["id"], "FATHER", True
    )

    # Fetch first guardian — should no longer be primary
    resp = await client.get(
        f"/api/v1/student-guardians/{g1_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["is_primary"] is False


async def test_remove_guardian(seeded_world, client):
    student_person = await _create_person(client, seeded_world.school_admin_a1.id, "StudentE")
    guardian_person = await _create_person(client, seeded_world.school_admin_a1.id, "GuardianE")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student_person["id"], "ADM-G005"
    )

    add_resp = await _add_guardian(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], guardian_person["id"]
    )
    guardian_id = add_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/student-guardians/{guardian_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert del_resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(
        f"/api/v1/student-guardians/{guardian_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert get_resp.status_code == 404


async def test_cross_tenant_guardian_not_visible(seeded_world, client):
    """Guardian created in school A should not be visible to school B."""
    student_person = await _create_person(client, seeded_world.school_admin_a1.id, "StudentF")
    guardian_person = await _create_person(client, seeded_world.school_admin_a1.id, "GuardianF")
    student = await _create_student(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student_person["id"], "ADM-G006"
    )

    add_resp = await _add_guardian(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id,
        student["id"], guardian_person["id"]
    )
    guardian_id = add_resp.json()["id"]

    # School B admin tries to access — should 404
    resp = await client.get(
        f"/api/v1/student-guardians/{guardian_id}",
        headers=school_auth(seeded_world.school_admin_a2.id, seeded_world.school_a2_id),
    )
    assert resp.status_code == 404
