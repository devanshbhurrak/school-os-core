"""
Load testing scenarios for School OS API.

Usage:
    pip install locust
    locust -f tests/load/locustfile.py --host http://localhost:8000

Key scenarios (V1 expected load: single school, 1000 students, 50 teachers):
    - GET /students list: p95 < 300ms
    - POST /attendance submit (40 students): p95 < 500ms
    - GET /announcements/feed: p95 < 300ms
    - Dashboard widgets (5 simultaneous): first paint < 2.5s
"""
from locust import HttpUser, task, between, tag
import json


class SchoolAdminUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login and store token."""
        resp = self.client.post("/api/v1/auth/login", json={
            "identifier": "admin@test.school",
            "password": "TestPass123!"
        })
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "X-School-ID": "test-school-id",  # configure for your test env
            }
        else:
            self.token = None
            self.headers = {}

    @task(5)
    @tag("list")
    def list_students(self):
        self.client.get("/api/v1/students?limit=20", headers=self.headers)

    @task(3)
    @tag("list")
    def list_teachers(self):
        self.client.get("/api/v1/teachers?limit=20", headers=self.headers)

    @task(2)
    @tag("list")
    def list_announcements_feed(self):
        self.client.get("/api/v1/announcements/feed?limit=10", headers=self.headers)

    @task(1)
    @tag("dashboard")
    def dashboard_widgets(self):
        """Simulate dashboard load — 5 concurrent widget requests."""
        self.client.get("/api/v1/students/counts", headers=self.headers, name="/students/counts")
        self.client.get("/api/v1/teachers/counts", headers=self.headers, name="/teachers/counts")
        self.client.get("/api/v1/attendance/today-summary", headers=self.headers, name="/attendance/today-summary")
        self.client.get("/api/v1/announcements?status=PUBLISHED&limit=3", headers=self.headers, name="/announcements (recent)")
        self.client.get("/api/v1/notifications/unread-count", headers=self.headers, name="/notifications/unread-count")

    @task(1)
    @tag("search")
    def search_students(self):
        self.client.get("/api/v1/search?q=test&limit=20", headers=self.headers)

    @task(1)
    @tag("attendance")
    def view_attendance_sessions(self):
        self.client.get("/api/v1/attendance-sessions?limit=20", headers=self.headers)


class TeacherUser(HttpUser):
    wait_time = between(2, 5)
    weight = 3  # More teachers than admins

    def on_start(self):
        resp = self.client.post("/api/v1/auth/login", json={
            "identifier": "teacher@test.school",
            "password": "TestPass123!"
        })
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "X-School-ID": "test-school-id",
            }
        else:
            self.token = None
            self.headers = {}

    @task(5)
    @tag("attendance")
    def take_attendance(self):
        """View attendance sessions."""
        self.client.get("/api/v1/attendance-sessions?limit=10", headers=self.headers)

    @task(3)
    @tag("list")
    def view_timetable(self):
        self.client.get("/api/v1/timetable-slots?limit=50", headers=self.headers)

    @task(2)
    @tag("list")
    def view_announcements(self):
        self.client.get("/api/v1/announcements/feed?limit=10", headers=self.headers)

    @task(1)
    @tag("notifications")
    def check_notifications(self):
        self.client.get("/api/v1/notifications/unread-count", headers=self.headers)
