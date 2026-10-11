"""Outbox monitoring permission codes (platform-admin only)."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_OUTBOX_LIST = registry.register(
    "platform", "outbox", Action.LIST, "List outbox events and dispatcher status"
)
