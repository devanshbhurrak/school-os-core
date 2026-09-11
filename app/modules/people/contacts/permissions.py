"""Contact permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_CONTACT_LIST = registry.register("people", "contact", Action.LIST, "List contacts")
P_CONTACT_READ = registry.register("people", "contact", Action.READ, "View a contact")
P_CONTACT_CREATE = registry.register("people", "contact", Action.CREATE, "Create a contact")
P_CONTACT_UPDATE = registry.register("people", "contact", Action.UPDATE, "Update a contact")
P_CONTACT_DELETE = registry.register("people", "contact", Action.DELETE, "Delete a contact")
