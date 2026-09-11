"""Academic module integration tests.

All school-scoped entities require X-School-ID header.
Covers CRUD, stale version, cross-tenant isolation, code uniqueness,
is_current logic, term date validation, and class subject filtering.
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
# Academic Classes
# ---------------------------------------------------------------------------


async def test_create_academic_class(seeded_world, client):
    resp = await client.post(
        "/api/v1/academic-classes",
        json={"code": "GRADE-5", "name": "Grade 5"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "GRADE-5"
    assert body["school_id"] == seeded_world.school_a1_id
    assert body["version"] == 1


async def test_get_academic_class(seeded_world, client):
    create = await client.post(
        "/api/v1/academic-classes",
        json={"code": "CLS-A", "name": "Class A"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    class_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/academic-classes/{class_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == class_id


async def test_update_academic_class(seeded_world, client):
    create = await client.post(
        "/api/v1/academic-classes",
        json={"code": "CLS-B", "name": "Class B"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    body = create.json()

    resp = await client.patch(
        f"/api/v1/academic-classes/{body['id']}",
        json={"name": "Class B Updated", "version": body["version"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Class B Updated"
    assert resp.json()["version"] == 2


async def test_delete_academic_class(seeded_world, client):
    create = await client.post(
        "/api/v1/academic-classes",
        json={"code": "CLS-DEL", "name": "Delete Me"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    body = create.json()

    del_resp = await client.request(
        "DELETE",
        f"/api/v1/academic-classes/{body['id']}",
        json={"version": body["version"]},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/academic-classes/{body['id']}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert get_resp.status_code == 404


async def test_academic_class_stale_version_409(seeded_world, client):
    create = await client.post(
        "/api/v1/academic-classes",
        json={"code": "CLS-STALE", "name": "Stale Test"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    body = create.json()

    await client.patch(
        f"/api/v1/academic-classes/{body['id']}",
        json={"name": "First Update", "version": 1},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )

    resp = await client.patch(
        f"/api/v1/academic-classes/{body['id']}",
        json={"name": "Stale Write", "version": 1},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "STALE_RESOURCE"


async def test_academic_class_code_duplicate_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    await client.post(
        "/api/v1/academic-classes",
        json={"code": "DUP-CLS", "name": "First"},
        headers=hdrs,
    )
    resp = await client.post(
        "/api/v1/academic-classes",
        json={"code": "DUP-CLS", "name": "Second"},
        headers=hdrs,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ACADEMIC_CLASS_CODE_TAKEN"


async def test_academic_class_cross_tenant_404(seeded_world, client):
    create = await client.post(
        "/api/v1/academic-classes",
        json={"code": "SECRET-CLS", "name": "Secret"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    class_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/academic-classes/{class_id}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Academic Years
# ---------------------------------------------------------------------------


async def test_create_academic_year(seeded_world, client):
    resp = await client.post(
        "/api/v1/academic-years",
        json={"code": "2024-25", "name": "Year 2024-25", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "2024-25"
    assert body["school_id"] == seeded_world.school_a1_id
    assert body["is_current"] is False


async def test_academic_year_is_current_only_one(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)

    r1 = await client.post(
        "/api/v1/academic-years",
        json={"code": "Y1", "name": "Year 1", "start_date": "2023-04-01", "end_date": "2024-03-31", "is_current": True},
        headers=hdrs,
    )
    year1_id = r1.json()["id"]

    r2 = await client.post(
        "/api/v1/academic-years",
        json={"code": "Y2", "name": "Year 2", "start_date": "2024-04-01", "end_date": "2025-03-31", "is_current": True},
        headers=hdrs,
    )
    assert r2.status_code == 201

    # Year 1 should no longer be current
    r1_get = await client.get(f"/api/v1/academic-years/{year1_id}", headers=hdrs)
    assert r1_get.json()["is_current"] is False
    assert r2.json()["is_current"] is True


async def test_academic_year_stale_version_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    create = await client.post(
        "/api/v1/academic-years",
        json={"code": "STALE-Y", "name": "Stale Year", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    body = create.json()

    await client.patch(
        f"/api/v1/academic-years/{body['id']}",
        json={"name": "Updated Once", "version": 1},
        headers=hdrs,
    )

    resp = await client.patch(
        f"/api/v1/academic-years/{body['id']}",
        json={"name": "Stale Write", "version": 1},
        headers=hdrs,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "STALE_RESOURCE"


async def test_academic_year_code_duplicate_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    await client.post(
        "/api/v1/academic-years",
        json={"code": "DUP-Y", "name": "First", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    resp = await client.post(
        "/api/v1/academic-years",
        json={"code": "DUP-Y", "name": "Second", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ACADEMIC_YEAR_CODE_TAKEN"


async def test_delete_academic_year(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    create = await client.post(
        "/api/v1/academic-years",
        json={"code": "DEL-Y", "name": "Del Year", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    body = create.json()
    del_resp = await client.request(
        "DELETE", f"/api/v1/academic-years/{body['id']}",
        json={"version": body["version"]}, headers=hdrs,
    )
    assert del_resp.status_code == 204


# ---------------------------------------------------------------------------
# Academic Terms
# ---------------------------------------------------------------------------


async def test_create_academic_term(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year = await client.post(
        "/api/v1/academic-years",
        json={"code": "T-YEAR", "name": "Term Year", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    year_id = year.json()["id"]

    resp = await client.post(
        "/api/v1/academic-terms",
        json={
            "academic_year_id": year_id,
            "code": "T1",
            "name": "Term 1",
            "start_date": "2024-04-01",
            "end_date": "2024-09-30",
        },
        headers=hdrs,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["academic_year_id"] == year_id
    assert body["code"] == "T1"


async def test_term_dates_outside_year_400(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year = await client.post(
        "/api/v1/academic-years",
        json={"code": "NARROW-Y", "name": "Narrow Year", "start_date": "2024-06-01", "end_date": "2024-12-31"},
        headers=hdrs,
    )
    year_id = year.json()["id"]

    resp = await client.post(
        "/api/v1/academic-terms",
        json={
            "academic_year_id": year_id,
            "code": "BAD-T",
            "name": "Bad Term",
            "start_date": "2024-01-01",  # before year start
            "end_date": "2024-06-30",
        },
        headers=hdrs,
    )
    assert resp.status_code == 400


async def test_list_terms_filtered_by_year(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year = await client.post(
        "/api/v1/academic-years",
        json={"code": "FILTER-Y", "name": "Filter Year", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    year_id = year.json()["id"]

    await client.post(
        "/api/v1/academic-terms",
        json={"academic_year_id": year_id, "code": "FT1", "name": "Filter T1",
              "start_date": "2024-04-01", "end_date": "2024-09-30"},
        headers=hdrs,
    )

    resp = await client.get(
        f"/api/v1/academic-terms?academic_year_id={year_id}",
        headers=hdrs,
    )
    assert resp.status_code == 200
    assert all(t["academic_year_id"] == year_id for t in resp.json()["items"])


async def test_academic_term_stale_version_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year = await client.post(
        "/api/v1/academic-years",
        json={"code": "ST-YEAR", "name": "Stale Term Year", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    year_id = year.json()["id"]
    term = await client.post(
        "/api/v1/academic-terms",
        json={"academic_year_id": year_id, "code": "ST1", "name": "Stale T1",
              "start_date": "2024-04-01", "end_date": "2024-09-30"},
        headers=hdrs,
    )
    body = term.json()
    await client.patch(
        f"/api/v1/academic-terms/{body['id']}",
        json={"name": "Updated", "version": 1}, headers=hdrs,
    )
    resp = await client.patch(
        f"/api/v1/academic-terms/{body['id']}",
        json={"name": "Stale Write", "version": 1}, headers=hdrs,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "STALE_RESOURCE"


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------


async def test_create_subject(seeded_world, client):
    resp = await client.post(
        "/api/v1/subjects",
        json={"code": "MATH", "name": "Mathematics", "subject_type": "CORE"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "MATH"
    assert body["subject_type"] == "CORE"


async def test_subject_code_duplicate_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    await client.post("/api/v1/subjects", json={"code": "DUP-SUB", "name": "First"}, headers=hdrs)
    resp = await client.post("/api/v1/subjects", json={"code": "DUP-SUB", "name": "Second"}, headers=hdrs)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SUBJECT_CODE_TAKEN"


async def test_subject_stale_version_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    create = await client.post("/api/v1/subjects", json={"code": "STALE-S", "name": "Stale"}, headers=hdrs)
    body = create.json()
    await client.patch(f"/api/v1/subjects/{body['id']}", json={"name": "Updated", "version": 1}, headers=hdrs)
    resp = await client.patch(f"/api/v1/subjects/{body['id']}", json={"name": "Stale", "version": 1}, headers=hdrs)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "STALE_RESOURCE"


async def test_subject_cross_tenant_404(seeded_world, client):
    create = await client.post(
        "/api/v1/subjects",
        json={"code": "SECRET-S", "name": "Secret Sub"},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    subject_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/subjects/{subject_id}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404


async def test_delete_subject(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    create = await client.post("/api/v1/subjects", json={"code": "DEL-S", "name": "Del Sub"}, headers=hdrs)
    body = create.json()
    del_resp = await client.request(
        "DELETE", f"/api/v1/subjects/{body['id']}", json={"version": body["version"]}, headers=hdrs
    )
    assert del_resp.status_code == 204


# ---------------------------------------------------------------------------
# Class Subjects
# ---------------------------------------------------------------------------


async def _setup_class_and_subject(client, school_admin_id: str, school_id: str):
    """Helper: create an academic class, subject and year; return their IDs."""
    hdrs = school_auth(school_admin_id, school_id)
    cls = await client.post(
        "/api/v1/academic-classes",
        json={"code": "CS-CLS", "name": "CS Class"},
        headers=hdrs,
    )
    sub = await client.post(
        "/api/v1/subjects",
        json={"code": "CS-SUB", "name": "CS Subject"},
        headers=hdrs,
    )
    year = await client.post(
        "/api/v1/academic-years",
        json={"code": "CS-Y", "name": "CS Year", "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    return cls.json()["id"], sub.json()["id"], year.json()["id"]


async def test_create_class_subject(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls_id, sub_id, year_id = await _setup_class_and_subject(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id
    )

    resp = await client.post(
        "/api/v1/class-subjects",
        json={"academic_class_id": cls_id, "subject_id": sub_id, "effective_from_year_id": year_id},
        headers=hdrs,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["academic_class_id"] == cls_id
    assert body["subject_id"] == sub_id


async def test_class_subject_duplicate_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls_id, sub_id, year_id = await _setup_class_and_subject(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id
    )
    payload = {"academic_class_id": cls_id, "subject_id": sub_id, "effective_from_year_id": year_id}
    await client.post("/api/v1/class-subjects", json=payload, headers=hdrs)
    resp = await client.post("/api/v1/class-subjects", json=payload, headers=hdrs)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CLASS_SUBJECT_ALREADY_EXISTS"


async def test_class_subject_filter_by_year(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls_id, sub_id, year_id = await _setup_class_and_subject(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id
    )
    await client.post(
        "/api/v1/class-subjects",
        json={"academic_class_id": cls_id, "subject_id": sub_id, "effective_from_year_id": year_id},
        headers=hdrs,
    )

    resp = await client.get(f"/api/v1/class-subjects?year_id={year_id}", headers=hdrs)
    assert resp.status_code == 200
    assert all(cs["effective_from_year_id"] == year_id for cs in resp.json()["items"])


async def test_class_subject_filter_by_class(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls_id, sub_id, year_id = await _setup_class_and_subject(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id
    )
    await client.post(
        "/api/v1/class-subjects",
        json={"academic_class_id": cls_id, "subject_id": sub_id, "effective_from_year_id": year_id},
        headers=hdrs,
    )

    resp = await client.get(f"/api/v1/class-subjects?academic_class_id={cls_id}", headers=hdrs)
    assert resp.status_code == 200
    assert all(cs["academic_class_id"] == cls_id for cs in resp.json()["items"])


async def test_delete_class_subject(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    cls_id, sub_id, year_id = await _setup_class_and_subject(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id
    )
    create = await client.post(
        "/api/v1/class-subjects",
        json={"academic_class_id": cls_id, "subject_id": sub_id, "effective_from_year_id": year_id},
        headers=hdrs,
    )
    cs_id = create.json()["id"]
    del_resp = await client.request("DELETE", f"/api/v1/class-subjects/{cs_id}", headers=hdrs)
    assert del_resp.status_code == 204


# ---------------------------------------------------------------------------
# Cohorts
# ---------------------------------------------------------------------------


async def _setup_year_and_class(client, school_admin_id: str, school_id: str, suffix: str = ""):
    hdrs = school_auth(school_admin_id, school_id)
    year = await client.post(
        "/api/v1/academic-years",
        json={"code": f"COH-Y{suffix}", "name": f"Cohort Year {suffix}",
              "start_date": "2024-04-01", "end_date": "2025-03-31"},
        headers=hdrs,
    )
    cls = await client.post(
        "/api/v1/academic-classes",
        json={"code": f"COH-CLS{suffix}", "name": f"Cohort Class {suffix}"},
        headers=hdrs,
    )
    return year.json()["id"], cls.json()["id"]


async def test_create_cohort(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year_id, cls_id = await _setup_year_and_class(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id
    )

    resp = await client.post(
        "/api/v1/cohorts",
        json={"academic_year_id": year_id, "academic_class_id": cls_id,
              "code": "SEC-A", "name": "Section A", "capacity": 40},
        headers=hdrs,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "SEC-A"
    assert body["capacity"] == 40


async def test_cohort_code_duplicate_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year_id, cls_id = await _setup_year_and_class(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, suffix="D"
    )
    payload = {"academic_year_id": year_id, "academic_class_id": cls_id, "code": "DUP-COH", "name": "Dup"}
    await client.post("/api/v1/cohorts", json=payload, headers=hdrs)
    resp = await client.post("/api/v1/cohorts", json=payload, headers=hdrs)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "COHORT_CODE_TAKEN"


async def test_cohort_stale_version_409(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year_id, cls_id = await _setup_year_and_class(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, suffix="S"
    )
    create = await client.post(
        "/api/v1/cohorts",
        json={"academic_year_id": year_id, "academic_class_id": cls_id, "code": "STALE-COH", "name": "Stale"},
        headers=hdrs,
    )
    body = create.json()
    await client.patch(f"/api/v1/cohorts/{body['id']}", json={"name": "Updated", "version": 1}, headers=hdrs)
    resp = await client.patch(f"/api/v1/cohorts/{body['id']}", json={"name": "Stale", "version": 1}, headers=hdrs)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "STALE_RESOURCE"


async def test_cohort_filter_by_year_and_class(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year_id, cls_id = await _setup_year_and_class(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, suffix="F"
    )
    await client.post(
        "/api/v1/cohorts",
        json={"academic_year_id": year_id, "academic_class_id": cls_id, "code": "SEC-F", "name": "Filter Section"},
        headers=hdrs,
    )

    resp = await client.get(
        f"/api/v1/cohorts?academic_year_id={year_id}&academic_class_id={cls_id}",
        headers=hdrs,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(c["academic_year_id"] == year_id for c in items)
    assert all(c["academic_class_id"] == cls_id for c in items)


async def test_cohort_cross_tenant_404(seeded_world, client):
    hdrs_a = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year_id, cls_id = await _setup_year_and_class(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, suffix="X"
    )
    create = await client.post(
        "/api/v1/cohorts",
        json={"academic_year_id": year_id, "academic_class_id": cls_id, "code": "SEC-X", "name": "Cross Sec"},
        headers=hdrs_a,
    )
    cohort_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/cohorts/{cohort_id}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404


async def test_delete_cohort(seeded_world, client):
    hdrs = school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id)
    year_id, cls_id = await _setup_year_and_class(
        client, seeded_world.school_admin_a1.id, seeded_world.school_a1_id, suffix="DEL"
    )
    create = await client.post(
        "/api/v1/cohorts",
        json={"academic_year_id": year_id, "academic_class_id": cls_id, "code": "DEL-COH", "name": "Del Cohort"},
        headers=hdrs,
    )
    body = create.json()
    del_resp = await client.request(
        "DELETE", f"/api/v1/cohorts/{body['id']}", json={"version": body["version"]}, headers=hdrs
    )
    assert del_resp.status_code == 204
