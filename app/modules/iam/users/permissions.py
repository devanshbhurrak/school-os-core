"""User permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_USER_LIST = registry.register("iam", "user", Action.LIST, "List users in an organization")
P_USER_READ = registry.register("iam", "user", Action.READ, "View a user")
P_USER_CREATE = registry.register("iam", "user", Action.CREATE, "Create a user account")
P_USER_UPDATE = registry.register("iam", "user", Action.UPDATE, "Update a user account")
P_USER_DELETE = registry.register("iam", "user", Action.DELETE, "Delete a user account")
P_USER_INVITE = registry.register("iam", "user", "invite", "Invite a user to an organization")
