"""Enrollment permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

ENROLLMENT_LIST = registry.register("students", "enrollment", Action.LIST, "List enrollments")
ENROLLMENT_READ = registry.register("students", "enrollment", Action.READ, "View enrollment")
ENROLLMENT_CREATE = registry.register("students", "enrollment", Action.CREATE, "Create enrollment")
ENROLLMENT_UPDATE = registry.register("students", "enrollment", Action.UPDATE, "Update enrollment")
ENROLLMENT_DELETE = registry.register("students", "enrollment", Action.DELETE, "Delete enrollment")
ENROLLMENT_TRANSFER = registry.register("students", "enrollment", "transfer", "Transfer student")
