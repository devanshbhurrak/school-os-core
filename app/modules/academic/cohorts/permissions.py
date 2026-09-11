"""Cohort permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_COHORT_LIST = registry.register("academic", "cohort", Action.LIST, "List cohorts")
P_COHORT_READ = registry.register("academic", "cohort", Action.READ, "View a cohort")
P_COHORT_CREATE = registry.register("academic", "cohort", Action.CREATE, "Create a cohort")
P_COHORT_UPDATE = registry.register("academic", "cohort", Action.UPDATE, "Update a cohort")
P_COHORT_DELETE = registry.register("academic", "cohort", Action.DELETE, "Delete a cohort")
