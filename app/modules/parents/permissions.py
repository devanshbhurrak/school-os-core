"""Parent permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_PARENT_LIST = registry.register("parents", "parent", Action.LIST, "List parents")
P_PARENT_READ = registry.register("parents", "parent", Action.READ, "View a parent")
P_PARENT_CREATE = registry.register("parents", "parent", Action.CREATE, "Create a parent")
P_PARENT_UPDATE = registry.register("parents", "parent", Action.UPDATE, "Update a parent")
P_PARENT_DELETE = registry.register("parents", "parent", Action.DELETE, "Delete a parent")

P_STUDENT_PARENT_CREATE = registry.register(
    "parents", "student_parent", Action.CREATE, "Link a parent to a student"
)
P_STUDENT_PARENT_DELETE = registry.register(
    "parents", "student_parent", Action.DELETE, "Unlink a parent from a student"
)
