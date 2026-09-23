"""Attendance permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

SESSION_LIST = registry.register("attendance", "session", Action.LIST, "List attendance sessions")
SESSION_READ = registry.register("attendance", "session", Action.READ, "View an attendance session")
SESSION_CREATE = registry.register("attendance", "session", Action.CREATE, "Create an attendance session")
SESSION_UPDATE = registry.register("attendance", "session", Action.UPDATE, "Update an attendance session")
SESSION_DELETE = registry.register("attendance", "session", Action.DELETE, "Delete an attendance session")
SESSION_SUBMIT = registry.register("attendance", "session", "submit", "Submit attendance")
SESSION_AMEND = registry.register("attendance", "session", "amend", "Amend submitted attendance")
RECORD_LIST = registry.register("attendance", "record", Action.LIST, "List attendance records")
RECORD_UPDATE = registry.register("attendance", "record", Action.UPDATE, "Update an attendance record")
