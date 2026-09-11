"""Subject permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_SUBJECT_LIST = registry.register("academic", "subject", Action.LIST, "List subjects")
P_SUBJECT_READ = registry.register("academic", "subject", Action.READ, "View a subject")
P_SUBJECT_CREATE = registry.register("academic", "subject", Action.CREATE, "Create a subject")
P_SUBJECT_UPDATE = registry.register("academic", "subject", Action.UPDATE, "Update a subject")
P_SUBJECT_DELETE = registry.register("academic", "subject", Action.DELETE, "Delete a subject")
