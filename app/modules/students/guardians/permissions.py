"""Guardian permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

GUARDIAN_LIST = registry.register("students", "guardian", Action.LIST, "List guardians")
GUARDIAN_READ = registry.register("students", "guardian", Action.READ, "View guardian")
GUARDIAN_CREATE = registry.register("students", "guardian", Action.CREATE, "Add guardian")
GUARDIAN_UPDATE = registry.register("students", "guardian", Action.UPDATE, "Update guardian")
GUARDIAN_DELETE = registry.register("students", "guardian", Action.DELETE, "Remove guardian")
