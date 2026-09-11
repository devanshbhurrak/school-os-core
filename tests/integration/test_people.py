"""People module integration tests: persons, addresses, contacts.

Covers CRUD flows and tenant isolation for org-scoped people data.
"""
from __future__ import annotations

from app.core.security import create_access_token


def auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


# ---------------------------------------------------------------------------
# Person CRUD
# ---------------------------------------------------------------------------


async def test_create_person(seeded_world, client):
    resp = await client.post(
        "/api/v1/persons",
        json={"first_name": "Arjun", "last_name": "Sharma", "primary_phone": "+919876543210"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["first_name"] == "Arjun"
    assert body["last_name"] == "Sharma"
    assert body["organization_id"] == seeded_world.org_a_id
    assert body["id"]
    assert body["version"] == 1


async def test_get_person(seeded_world, client):
    create = await client.post(
        "/api/v1/persons",
        json={"first_name": "Priya", "last_name": "Nair"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    person_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/persons/{person_id}",
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == person_id


async def test_update_person(seeded_world, client):
    create = await client.post(
        "/api/v1/persons",
        json={"first_name": "Ravi", "last_name": "Kumar"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    body = create.json()

    resp = await client.patch(
        f"/api/v1/persons/{body['id']}",
        json={"first_name": "Ravi Updated", "version": body["version"]},
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Ravi Updated"
    assert resp.json()["version"] == 2


async def test_update_person_stale_version_raises_409(seeded_world, client):
    create = await client.post(
        "/api/v1/persons",
        json={"first_name": "Stale", "last_name": "Test"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    body = create.json()

    # First update succeeds (version 1 → 2)
    await client.patch(
        f"/api/v1/persons/{body['id']}",
        json={"first_name": "Updated Once", "version": 1},
        headers=auth_header(seeded_world.admin_a.id),
    )

    # Second update with stale version should fail
    resp = await client.patch(
        f"/api/v1/persons/{body['id']}",
        json={"first_name": "Stale Write", "version": 1},
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "STALE_RESOURCE"


async def test_delete_person(seeded_world, client):
    create = await client.post(
        "/api/v1/persons",
        json={"first_name": "Delete", "last_name": "Me"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    body = create.json()

    resp = await client.request(
        "DELETE",
        f"/api/v1/persons/{body['id']}",
        json={"version": body["version"]},
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/persons/{body['id']}",
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert get_resp.status_code == 404


async def test_list_persons_returns_own_org_only(seeded_world, client):
    # Create a person in org A
    await client.post(
        "/api/v1/persons",
        json={"first_name": "Org A Person"},
        headers=auth_header(seeded_world.admin_a.id),
    )

    # Org B admin should see zero persons (empty org B)
    resp = await client.get(
        "/api/v1/persons",
        headers=auth_header(seeded_world.admin_b.id),
    )
    assert resp.status_code == 200
    body = resp.json()
    ids = [p["id"] for p in body["items"]]
    # Org A persons must not appear for org B admin
    resp_a = await client.get(
        "/api/v1/persons",
        headers=auth_header(seeded_world.admin_a.id),
    )
    person_ids_a = {p["id"] for p in resp_a.json()["items"]}
    assert person_ids_a.isdisjoint(set(ids))


async def test_person_search(seeded_world, client):
    await client.post(
        "/api/v1/persons",
        json={"first_name": "SearchableFirst", "last_name": "SearchableLast"},
        headers=auth_header(seeded_world.admin_a.id),
    )

    resp = await client.get(
        "/api/v1/persons?search=Searchable",
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 200
    assert any("Searchable" in p["first_name"] for p in resp.json()["items"])


async def test_cross_tenant_person_is_404(seeded_world, client):
    # Create a person in org A
    create = await client.post(
        "/api/v1/persons",
        json={"first_name": "Org A Secret"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    person_id = create.json()["id"]

    # Org B admin should not see it
    resp = await client.get(
        f"/api/v1/persons/{person_id}",
        headers=auth_header(seeded_world.admin_b.id),
    )
    assert resp.status_code == 404


async def test_teacher_cannot_create_person(seeded_world, client):
    resp = await client.post(
        "/api/v1/persons",
        json={"first_name": "Unauthorized"},
        headers=auth_header(seeded_world.teacher_a1.id),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cursor pagination
# ---------------------------------------------------------------------------


async def test_cursor_pagination_stable(seeded_world, client):
    """Create several persons and verify cursor pagination returns all without duplicates."""
    names = [f"Person{i:02d}" for i in range(5)]
    created_ids: list[str] = []
    for name in names:
        r = await client.post(
            "/api/v1/persons",
            json={"first_name": name},
            headers=auth_header(seeded_world.admin_a.id),
        )
        created_ids.append(r.json()["id"])

    collected: list[str] = []
    cursor: str | None = None
    while True:
        url = "/api/v1/persons?limit=2"
        if cursor:
            url += f"&cursor={cursor}"
        resp = await client.get(url, headers=auth_header(seeded_world.admin_a.id))
        assert resp.status_code == 200
        page = resp.json()
        collected.extend(p["id"] for p in page["items"])
        cursor = page.get("next_cursor")
        if not page["has_more"]:
            break

    # Every created person must appear exactly once
    for pid in created_ids:
        assert collected.count(pid) == 1, f"Person {pid} appeared {collected.count(pid)} times"


# ---------------------------------------------------------------------------
# Address CRUD
# ---------------------------------------------------------------------------


async def test_create_and_get_address(seeded_world, client):
    # Create a person first
    person = await client.post(
        "/api/v1/persons",
        json={"first_name": "AddrTest"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    person_id = person.json()["id"]

    resp = await client.post(
        "/api/v1/addresses",
        json={
            "entity_type": "PERSON",
            "entity_id": person_id,
            "address_type": "RESIDENTIAL",
            "line1": "42 MG Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560001",
        },
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["city"] == "Bengaluru"
    assert body["organization_id"] == seeded_world.org_a_id

    get_resp = await client.get(
        f"/api/v1/addresses/{body['id']}",
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]


async def test_cross_tenant_address_is_404(seeded_world, client):
    person = await client.post(
        "/api/v1/persons",
        json={"first_name": "SecretAddr"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    addr = await client.post(
        "/api/v1/addresses",
        json={"entity_type": "PERSON", "entity_id": person.json()["id"], "city": "Mumbai"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    addr_id = addr.json()["id"]

    resp = await client.get(
        f"/api/v1/addresses/{addr_id}",
        headers=auth_header(seeded_world.admin_b.id),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Contact CRUD
# ---------------------------------------------------------------------------


async def test_create_and_get_contact(seeded_world, client):
    person = await client.post(
        "/api/v1/persons",
        json={"first_name": "ContactTest"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    person_id = person.json()["id"]

    resp = await client.post(
        "/api/v1/contacts",
        json={
            "entity_type": "PERSON",
            "entity_id": person_id,
            "contact_type": "PHONE",
            "value": "+919876543211",
            "is_primary": True,
        },
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["value"] == "+919876543211"
    assert body["organization_id"] == seeded_world.org_a_id

    get_resp = await client.get(
        f"/api/v1/contacts/{body['id']}",
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]


async def test_cross_tenant_contact_is_404(seeded_world, client):
    person = await client.post(
        "/api/v1/persons",
        json={"first_name": "SecretContact"},
        headers=auth_header(seeded_world.admin_a.id),
    )
    contact = await client.post(
        "/api/v1/contacts",
        json={
            "entity_type": "PERSON",
            "entity_id": person.json()["id"],
            "contact_type": "EMAIL",
            "value": "secret@test.local",
        },
        headers=auth_header(seeded_world.admin_a.id),
    )
    contact_id = contact.json()["id"]

    resp = await client.get(
        f"/api/v1/contacts/{contact_id}",
        headers=auth_header(seeded_world.admin_b.id),
    )
    assert resp.status_code == 404
