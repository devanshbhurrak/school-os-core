"""Notification permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_NOTIFICATION_LIST = registry.register("notifications", "notification", Action.LIST, "List own notifications")
P_NOTIFICATION_UPDATE = registry.register("notifications", "notification", Action.UPDATE, "Mark notifications as read")
