"""Student permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_STUDENT_LIST = registry.register("students", "student", Action.LIST, "List students")
P_STUDENT_READ = registry.register("students", "student", Action.READ, "View a student")
P_STUDENT_CREATE = registry.register("students", "student", Action.CREATE, "Create a student")
P_STUDENT_UPDATE = registry.register("students", "student", Action.UPDATE, "Update a student")
P_STUDENT_DELETE = registry.register("students", "student", Action.DELETE, "Delete a student")
