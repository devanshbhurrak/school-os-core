"""AcademicTerm permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_ACADEMIC_TERM_LIST = registry.register("academic", "academic_term", Action.LIST, "List academic terms")
P_ACADEMIC_TERM_READ = registry.register("academic", "academic_term", Action.READ, "View an academic term")
P_ACADEMIC_TERM_CREATE = registry.register("academic", "academic_term", Action.CREATE, "Create an academic term")
P_ACADEMIC_TERM_UPDATE = registry.register("academic", "academic_term", Action.UPDATE, "Update an academic term")
P_ACADEMIC_TERM_DELETE = registry.register("academic", "academic_term", Action.DELETE, "Delete an academic term")
