"""Report permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_EXPORT_CREATE = registry.register("reports", "export", Action.CREATE, "Create an export job")
P_EXPORT_LIST = registry.register("reports", "export", Action.LIST, "List export jobs")
P_EXPORT_READ = registry.register("reports", "export", Action.READ, "View an export job")
