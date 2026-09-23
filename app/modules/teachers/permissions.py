"""Teacher permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_TEACHER_LIST = registry.register("teachers", "teacher", Action.LIST, "List teachers")
P_TEACHER_READ = registry.register("teachers", "teacher", Action.READ, "View a teacher")
P_TEACHER_CREATE = registry.register("teachers", "teacher", Action.CREATE, "Create a teacher")
P_TEACHER_UPDATE = registry.register("teachers", "teacher", Action.UPDATE, "Update a teacher")
P_TEACHER_DELETE = registry.register("teachers", "teacher", Action.DELETE, "Delete a teacher")

P_ASSIGNMENT_LIST = registry.register("teachers", "assignment", Action.LIST, "List teacher assignments")
P_ASSIGNMENT_READ = registry.register("teachers", "assignment", Action.READ, "View a teacher assignment")
P_ASSIGNMENT_CREATE = registry.register("teachers", "assignment", Action.CREATE, "Create a teacher assignment")
P_ASSIGNMENT_UPDATE = registry.register("teachers", "assignment", Action.UPDATE, "Update a teacher assignment")
P_ASSIGNMENT_DELETE = registry.register("teachers", "assignment", Action.DELETE, "End a teacher assignment")
