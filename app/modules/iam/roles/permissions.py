"""Role permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_ROLE_LIST = registry.register("iam", "role", Action.LIST, "List roles")
P_ROLE_READ = registry.register("iam", "role", Action.READ, "View a role")
P_ROLE_CREATE = registry.register("iam", "role", Action.CREATE, "Create a role")
P_ROLE_UPDATE = registry.register("iam", "role", Action.UPDATE, "Update a role")
P_ROLE_DELETE = registry.register("iam", "role", Action.DELETE, "Delete a role")
