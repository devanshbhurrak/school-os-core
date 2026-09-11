"""Address permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_ADDRESS_LIST = registry.register("people", "address", Action.LIST, "List addresses")
P_ADDRESS_READ = registry.register("people", "address", Action.READ, "View an address")
P_ADDRESS_CREATE = registry.register("people", "address", Action.CREATE, "Create an address")
P_ADDRESS_UPDATE = registry.register("people", "address", Action.UPDATE, "Update an address")
P_ADDRESS_DELETE = registry.register("people", "address", Action.DELETE, "Delete an address")
