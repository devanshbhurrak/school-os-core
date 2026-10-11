"""
Load testing scenarios for School OS API (Phase 3, C3).

Usage:
    pip install locust
    LOCUST_USERNAME=admin@demo.test LOCUST_PASSWORD='...' LOCUST_SCHOOL_ID='<ulid>' \\
        locust -f tests/load/locustfile.py --host http://localhost:8000

Seed the target database first (1000 students, 50 teachers) via:
    python scripts/bootstrap.py   # demo world
    # then bulk-import generated CSVs through POST /api/v1/import-jobs/upload

p95 targets (single school, 1000 students / 50 teachers):
    - GET /students list: p95 < 300ms
    - POST /attendance submit (40 students): p95 < 500ms
    - GET /announcements/feed (10 concurrent): p95 < 300ms
    - Dashboard widgets (5 requests): first paint < 2.5s
    - Bulk import 1000-row CSV: < 60s (see BulkImportUser)

Scenarios:
    - SchoolAdminUser: list/browse traffic (weight 1)
    - TeacherUser: attendance + timetable traffic (weight 3)
    - MorningRushUser: 20 teachers submitting attendance at once (spawn with
      `-u 20` and tag filter `morning-rush`)
    - BulkImportUser: 1000-row CSV upload timing (run alone, `-u 1`)
"""
from __future__ import annotations

import csv
import io
import os
import time

from locust import HttpUser, constant_throughput, task, between, tag

USERNAME = os.environ.get("LOCUST_USERNAME", "admin@demo.test")
PASSWORD = os.environ.get("LOCUST_PASSWORD", "changeme")
SCHOOL_ID = os.environ.get("LOCUST_SCHOOL_ID", "")


class AuthenticatedUser(HttpUser):
    abstract = True

    def on_start(self):
        """Login and store token + school headers."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"identifier": USERNAME, "password": PASSWORD},
            name="/auth/login",
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            if SCHOOL_ID:
                self.headers["X-School-ID"] = SCHOOL_ID
        else:
            self.token = None
            self.headers = {}


class SchoolAdminUser(AuthenticatedUser):
    wait_time = between(1, 3)

    @task(5)
    @tag("list")
    def list_students(self):
        self.client.get("/api/v1/students?limit=20", headers=self.headers, name="/students")

    @task(3)
    @tag("list")
    def list_teachers(self):
        self.client.get("/api/v1/teachers?limit=20", headers=self.headers, name="/teachers")

    @task(2)
    @tag("list")
    def list_announcements_feed(self):
        self.client.get("/api/v1/announcements/feed?limit=10", headers=self.headers, name="/announcements/feed")

    @task(1)
    @tag("dashboard")
    def dashboard_widgets(self):
        """Dashboard load — 5 sequential widget requests (first paint < 2.5s)."""
        self.client.get("/api/v1/students/counts", headers=self.headers, name="/students/counts")
        self.client.get("/api/v1/teachers/counts", headers=self.headers, name="/teachers/counts")
        self.client.get("/api/v1/attendance/today-summary", headers=self.headers, name="/attendance/today-summary")
        self.client.get("/api/v1/announcements?limit=3", headers=self.headers, name="/announcements (recent)")
        self.client.get("/api/v1/notifications/unread-count", headers=self.headers, name="/notifications/unread-count")

    @task(1)
    @tag("search")
    def search_students(self):
        self.client.get("/api/v1/search?q=aar&limit=20", headers=self.headers, name="/search")

    @task(1)
    @tag("attendance")
    def view_attendance_sessions(self):
        self.client.get("/api/v1/attendance-sessions?limit=20", headers=self.headers, name="/attendance-sessions")


class TeacherUser(AuthenticatedUser):
    wait_time = between(2, 5)
    weight = 3  # More teachers than admins

    @task(5)
    @tag("attendance")
    def view_sessions(self):
        self.client.get("/api/v1/attendance-sessions?limit=10", headers=self.headers, name="/attendance-sessions")

    @task(3)
    @tag("list")
    def view_timetable(self):
        self.client.get("/api/v1/timetable-slots?limit=50", headers=self.headers, name="/timetable-slots")

    @task(2)
    @tag("list")
    def view_announcements(self):
        self.client.get("/api/v1/announcements/feed?limit=10", headers=self.headers, name="/announcements/feed")

    @task(1)
    @tag("notifications")
    def check_notifications(self):
        self.client.get("/api/v1/notifications/unread-count", headers=self.headers, name="/notifications/unread-count")


class MorningRushUser(AuthenticatedUser):
    """Morning attendance rush: 20 teachers submitting at once.

    Run: locust -f tests/load/locustfile.py --host ... -u 20 -r 20 --tags morning-rush
    Each user lists sessions and submits the first DRAFT one it finds.
    """

    wait_time = constant_throughput(1)

    @task
    @tag("morning-rush", "attendance")
    def submit_morning_attendance(self):
        sessions = self.client.get(
            "/api/v1/attendance-sessions?limit=5", headers=self.headers, name="/attendance-sessions"
        )
        if sessions.status_code != 200:
            return
        drafts = [s for s in sessions.json().get("items", []) if s.get("status") == "DRAFT"]
        if not drafts:
            return
        target = drafts[0]
        with self.client.post(
            f"/api/v1/attendance-sessions/{target['id']}/submit",
            json={"version": target["version"]},
            headers=self.headers,
            name="/attendance-sessions/{id}/submit",
            catch_response=True,
        ) as resp:
            # 409 means a colleague submitted first — expected under rush load.
            if resp.status_code in (200, 409):
                resp.success()


def _thousand_row_student_csv() -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["first_name", "last_name", "primary_email", "primary_phone", "admission_number", "admission_date", "status"])
    for i in range(1000):
        writer.writerow([
            f"Load{i}", "Student", f"load{i}@test.local", f"+1555000{i:04d}",
            f"ADM-LOAD-{i:04d}", "2024-01-15", "ACTIVE",
        ])
    return buf.getvalue().encode()


class BulkImportUser(AuthenticatedUser):
    """Bulk import timing: 1000-row CSV must complete in < 60s.

    Run alone: locust ... -u 1 -r 1 --tags bulk-import
    """

    wait_time = between(10, 20)

    @task
    @tag("bulk-import")
    def import_thousand_students(self):
        payload = _thousand_row_student_csv()
        started = time.monotonic()
        with self.client.post(
            "/api/v1/import-jobs/upload",
            files={"file": ("load-1000.csv", payload, "text/csv")},
            data={"resource_type": "STUDENTS"},
            headers=self.headers,
            name="/import-jobs/upload (1000 rows)",
            catch_response=True,
        ) as resp:
            elapsed = time.monotonic() - started
            if resp.status_code == 200 and elapsed < 60:
                resp.success()
            elif resp.status_code == 200:
                resp.failure(f"Import took {elapsed:.1f}s, target < 60s")
            else:
                resp.failure(f"HTTP {resp.status_code}: {resp.text[:200]}")
