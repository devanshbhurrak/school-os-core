"""School permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_SCHOOL_LIST = registry.register("iam", "school", Action.LIST, "List schools")
P_SCHOOL_READ = registry.register("iam", "school", Action.READ, "View a school")
P_SCHOOL_CREATE = registry.register("iam", "school", Action.CREATE, "Create a school")
P_SCHOOL_UPDATE = registry.register("iam", "school", Action.UPDATE, "Update a school")
P_SCHOOL_DELETE = registry.register("iam", "school", Action.DELETE, "Delete a school")
