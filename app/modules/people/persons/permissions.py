"""Person permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_PERSON_LIST = registry.register("people", "person", Action.LIST, "List persons")
P_PERSON_READ = registry.register("people", "person", Action.READ, "View a person")
P_PERSON_CREATE = registry.register("people", "person", Action.CREATE, "Create a person")
P_PERSON_UPDATE = registry.register("people", "person", Action.UPDATE, "Update a person")
P_PERSON_DELETE = registry.register("people", "person", Action.DELETE, "Delete a person")
P_PERSON_MERGE = registry.register("people", "person", "merge", "Merge duplicate persons")
