"""AcademicYear permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_ACADEMIC_YEAR_LIST = registry.register("academic", "academic_year", Action.LIST, "List academic years")
P_ACADEMIC_YEAR_READ = registry.register("academic", "academic_year", Action.READ, "View an academic year")
P_ACADEMIC_YEAR_CREATE = registry.register("academic", "academic_year", Action.CREATE, "Create an academic year")
P_ACADEMIC_YEAR_UPDATE = registry.register("academic", "academic_year", Action.UPDATE, "Update an academic year")
P_ACADEMIC_YEAR_DELETE = registry.register("academic", "academic_year", Action.DELETE, "Delete an academic year")
