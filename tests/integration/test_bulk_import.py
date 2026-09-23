"""Bulk import/export integration tests."""
from __future__ import annotations

import io

from app.core.security import create_access_token


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def school_auth(user_id: str, school_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id)}",
        "X-School-ID": school_id,
    }


def _make_student_csv(rows: list[dict]) -> bytes:
    import csv
    import io as _io
    fieldnames = ["first_name", "last_name", "primary_email", "primary_phone", "admission_number", "admission_date", "status"]
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _make_teacher_csv(rows: list[dict]) -> bytes:
    import csv
    import io as _io
    fieldnames = ["first_name", "last_name", "primary_email", "primary_phone", "employee_number", "designation", "joining_date", "status"]
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


async def test_upload_valid_students_csv(seeded_world, client):
    """Uploading a valid students CSV creates a COMPLETED job and creates students."""
    csv_bytes = _make_student_csv([
        {"first_name": "Alice", "last_name": "Smith", "admission_number": "ADM-001", "admission_date": "2024-01-15"},
        {"first_name": "Bob", "last_name": "Jones", "admission_number": "ADM-002", "admission_date": "2024-02-01"},
    ])
    resp = await client.post(
        "/api/v1/import-jobs/upload",
        data={"resource_type": "students"},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["total_rows"] == 2
    assert body["success_rows"] == 2
    assert body["failed_rows"] == 0
    assert body["error_summary"] is None
    assert body["resource_type"] == "students"


async def test_upload_csv_with_some_invalid_rows(seeded_world, client):
    """Uploading a CSV with some invalid rows creates a PARTIAL job with error summary."""
    csv_bytes = _make_student_csv([
        {"first_name": "Alice", "last_name": "Smith", "admission_number": "ADM-001", "admission_date": "2024-01-15"},
        # missing admission_number and bad date
        {"first_name": "Bob", "last_name": "Jones", "admission_number": "", "admission_date": "not-a-date"},
    ])
    resp = await client.post(
        "/api/v1/import-jobs/upload",
        data={"resource_type": "students"},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "PARTIAL"
    assert body["success_rows"] == 1
    assert body["failed_rows"] >= 1
    assert body["error_summary"] is not None
    assert len(body["error_summary"]) > 0


async def test_upload_invalid_csv_format(seeded_world, client):
    """Uploading an entirely invalid (binary) file creates a FAILED job."""
    resp = await client.post(
        "/api/v1/import-jobs/upload",
        data={"resource_type": "students"},
        files={"file": ("bad.csv", io.BytesIO(b"\xff\xfe\x00" * 100), "text/csv")},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    # Either 422 validation error or a FAILED job
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        assert resp.json()["status"] == "FAILED"


async def test_upload_all_invalid_rows(seeded_world, client):
    """Uploading a CSV where all rows fail creates a FAILED job."""
    csv_bytes = _make_student_csv([
        # Missing required fields
        {"first_name": "", "last_name": "Smith", "admission_number": "", "admission_date": ""},
    ])
    resp = await client.post(
        "/api/v1/import-jobs/upload",
        data={"resource_type": "students"},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["success_rows"] == 0


async def test_download_student_export(seeded_world, client):
    """Export endpoint returns CSV with correct headers."""
    resp = await client.get(
        "/api/v1/exports/students",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    # Should have the CSV header row
    content = resp.text
    assert "first_name" in content
    assert "admission_number" in content


async def test_download_template(seeded_world, client):
    """Template endpoint returns CSV with headers only (no data rows)."""
    resp = await client.get(
        "/api/v1/imports/template/students",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    lines = [l for l in resp.text.strip().splitlines() if l]
    # Only the header line, no data rows
    assert len(lines) == 1
    assert "first_name" in lines[0]


async def test_get_import_job_by_id(seeded_world, client):
    """Can read a specific import job by ID."""
    csv_bytes = _make_student_csv([
        {"first_name": "Alice", "admission_number": "ADM-001", "admission_date": "2024-01-15"},
    ])
    upload_resp = await client.post(
        "/api/v1/import-jobs/upload",
        data={"resource_type": "students"},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert upload_resp.status_code == 200
    job_id = upload_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/import-jobs/{job_id}",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


async def test_list_import_jobs(seeded_world, client):
    """Can list import jobs for a school."""
    csv_bytes = _make_student_csv([
        {"first_name": "Alice", "admission_number": "ADM-001", "admission_date": "2024-01-15"},
    ])
    await client.post(
        "/api/v1/import-jobs/upload",
        data={"resource_type": "students"},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )

    resp = await client.get(
        "/api/v1/import-jobs",
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    jobs = resp.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1


async def test_cross_tenant_job_isolation(seeded_world, client):
    """A job created for school A is not visible to school B."""
    csv_bytes = _make_student_csv([
        {"first_name": "Alice", "admission_number": "ADM-001", "admission_date": "2024-01-15"},
    ])
    upload_resp = await client.post(
        "/api/v1/import-jobs/upload",
        data={"resource_type": "students"},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert upload_resp.status_code == 200
    job_id = upload_resp.json()["id"]

    # School B cannot see the job
    resp = await client.get(
        f"/api/v1/import-jobs/{job_id}",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404


async def test_teacher_import(seeded_world, client):
    """Uploading a valid teachers CSV creates a COMPLETED job."""
    csv_bytes = _make_teacher_csv([
        {"first_name": "Carol", "last_name": "White", "employee_number": "EMP-001"},
    ])
    resp = await client.post(
        "/api/v1/import-jobs/upload",
        data={"resource_type": "teachers"},
        files={"file": ("teachers.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["resource_type"] == "teachers"
    assert body["success_rows"] == 1
