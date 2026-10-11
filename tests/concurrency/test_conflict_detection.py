"""Concurrency conflict tests (Phase 3, C2): double enrollment & assignment races.

Uses `asyncio.gather()` to fire truly concurrent requests at the API. The
database (partial unique indexes) is the final arbiter — application-level
checks alone have a check-then-insert race — and services map the resulting
integrity errors to 409 CONFLICT.
"""
from __future__ import annotations

import asyncio

from app.core.security import create_access_token


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def school_auth(user_id: str, school_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id)}",
        "X-School-ID": school_id,
    }


async def _setup_academic_stack(client, user_id: str, school_id: str, suffix: str = "CC") -> dict:
    """Create year + class + cohort + subject, returning their ids."""
    year = (await client.post(
        "/api/v1/academic-years",
        json={
            "code": f"{suffix}-Y", "name": f"Year {suffix}",
            "start_date": "2024-04-01", "end_date": "2025-03-31",
        },
        headers=school_auth(user_id, school_id),
    )).json()
    cls = (await client.post(
        "/api/v1/academic-classes",
        json={"code": f"{suffix}-CLS", "name": f"Class {suffix}", "level": 1},
        headers=school_auth(user_id, school_id),
    )).json()
    cohort = (await client.post(
        "/api/v1/cohorts",
        json={
            "name": f"Section {suffix}",
            "academic_year_id": year["id"],
            "academic_class_id": cls["id"],
        },
        headers=school_auth(user_id, school_id),
    )).json()
    subject = (await client.post(
        "/api/v1/subjects",
        json={"code": f"{suffix}-SUB", "name": f"Subject {suffix}"},
        headers=school_auth(user_id, school_id),
    )).json()
    return {"year": year, "class": cls, "cohort": cohort, "subject": subject}


async def _create_student(client, user_id: str, school_id: str, adm: str) -> dict:
    person = (await client.post(
        "/api/v1/persons",
        json={"first_name": "Race", "last_name": "Condition"},
        headers=auth(user_id),
    )).json()
    student = (await client.post(
        "/api/v1/students",
        json={
            "person_id": person["id"],
            "admission_number": adm,
            "admission_date": "2024-01-15",
        },
        headers=school_auth(user_id, school_id),
    )).json()
    return student


async def _create_teacher(client, user_id: str, school_id: str, emp: str) -> dict:
    person = (await client.post(
        "/api/v1/persons",
        json={"first_name": "Race", "last_name": "Teacher"},
        headers=auth(user_id),
    )).json()
    teacher = (await client.post(
        "/api/v1/teachers",
        json={"person_id": person["id"], "employee_number": emp, "status": "ACTIVE"},
        headers=school_auth(user_id, school_id),
    )).json()
    return teacher


async def test_concurrent_enrollment_prevents_double_active(seeded_world, client):
    """Two concurrent enrollments for one student+year → exactly one wins."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    stack = await _setup_academic_stack(client, u.id, sid, suffix="ENR")
    student = await _create_student(client, u.id, sid, "ADM-ENR-001")

    payload = {
        "student_id": student["id"],
        "academic_year_id": stack["year"]["id"],
        "academic_class_id": stack["class"]["id"],
        "cohort_id": stack["cohort"]["id"],
        "start_date": "2024-04-01",
    }
    headers = school_auth(u.id, sid)

    resp_a, resp_b = await asyncio.gather(
        client.post("/api/v1/enrollments", json=payload, headers=headers),
        client.post("/api/v1/enrollments", json=payload, headers=headers),
    )

    statuses = sorted([resp_a.status_code, resp_b.status_code])
    assert statuses == [201, 409], (resp_a.status_code, resp_a.text, resp_b.status_code, resp_b.text)

    loser = resp_a if resp_a.status_code == 409 else resp_b
    assert loser.json()["error"]["code"] == "ALREADY_ENROLLED"


async def test_concurrent_teacher_assignment_conflict(seeded_world, client):
    """Two concurrent CLASS_TEACHER assignments for one cohort → one wins."""
    u = seeded_world.school_admin_a1
    sid = seeded_world.school_a1_id

    stack = await _setup_academic_stack(client, u.id, sid, suffix="ASG")
    teacher = await _create_teacher(client, u.id, sid, "EMP-ASG-001")

    payload = {
        "teacher_id": teacher["id"],
        "cohort_id": stack["cohort"]["id"],
        "academic_year_id": stack["year"]["id"],
        "role": "CLASS_TEACHER",
        "start_date": "2024-04-01",
    }
    headers = school_auth(u.id, sid)

    resp_a, resp_b = await asyncio.gather(
        client.post("/api/v1/teacher-assignments", json=payload, headers=headers),
        client.post("/api/v1/teacher-assignments", json=payload, headers=headers),
    )

    statuses = sorted([resp_a.status_code, resp_b.status_code])
    assert statuses == [201, 409], (resp_a.status_code, resp_a.text, resp_b.status_code, resp_b.text)

    loser = resp_a if resp_a.status_code == 409 else resp_b
    assert loser.json()["error"]["code"] == "ASSIGNMENT_CONFLICT"
