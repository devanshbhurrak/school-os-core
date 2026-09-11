"""AcademicClass permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_ACADEMIC_CLASS_LIST = registry.register("academic", "academic_class", Action.LIST, "List academic classes")
P_ACADEMIC_CLASS_READ = registry.register("academic", "academic_class", Action.READ, "View an academic class")
P_ACADEMIC_CLASS_CREATE = registry.register("academic", "academic_class", Action.CREATE, "Create an academic class")
P_ACADEMIC_CLASS_UPDATE = registry.register("academic", "academic_class", Action.UPDATE, "Update an academic class")
P_ACADEMIC_CLASS_DELETE = registry.register("academic", "academic_class", Action.DELETE, "Delete an academic class")
