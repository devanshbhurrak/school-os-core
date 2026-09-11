"""Organization permission codes. Declared here, synced to the DB by
scripts/sync_permissions.py, and referenced by routes via `require()`."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_ORG_LIST = registry.register("iam", "organization", Action.LIST, "List organizations")
P_ORG_READ = registry.register("iam", "organization", Action.READ, "View an organization")
P_ORG_CREATE = registry.register("iam", "organization", Action.CREATE, "Create an organization")
P_ORG_UPDATE = registry.register("iam", "organization", Action.UPDATE, "Update an organization")
P_ORG_DELETE = registry.register("iam", "organization", Action.DELETE, "Delete an organization")
