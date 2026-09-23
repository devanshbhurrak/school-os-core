"""Announcement permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_ANNOUNCEMENT_LIST = registry.register("announcements", "announcement", Action.LIST, "List announcements")
P_ANNOUNCEMENT_READ = registry.register("announcements", "announcement", Action.READ, "View an announcement")
P_ANNOUNCEMENT_CREATE = registry.register("announcements", "announcement", Action.CREATE, "Create an announcement")
P_ANNOUNCEMENT_UPDATE = registry.register("announcements", "announcement", Action.UPDATE, "Update an announcement")
P_ANNOUNCEMENT_DELETE = registry.register("announcements", "announcement", Action.DELETE, "Delete an announcement")
P_ANNOUNCEMENT_PUBLISH = registry.register("announcements", "announcement", "publish", "Publish an announcement")
P_ANNOUNCEMENT_ARCHIVE = registry.register("announcements", "announcement", Action.ARCHIVE, "Archive an announcement")
