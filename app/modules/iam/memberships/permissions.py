"""Membership permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_MEMBERSHIP_LIST = registry.register("iam", "membership", Action.LIST, "List memberships")
P_MEMBERSHIP_READ = registry.register("iam", "membership", Action.READ, "View a membership")
P_MEMBERSHIP_CREATE = registry.register("iam", "membership", Action.CREATE, "Create a membership")
P_MEMBERSHIP_UPDATE = registry.register("iam", "membership", Action.UPDATE, "Update a membership")
P_MEMBERSHIP_DELETE = registry.register("iam", "membership", Action.DELETE, "End a membership")
P_MEMBERSHIP_GRANT_ROLE = registry.register("iam", "membership", "grant_role", "Grant a role to a membership")
P_MEMBERSHIP_REVOKE_ROLE = registry.register("iam", "membership", "revoke_role", "Revoke a role from a membership")
