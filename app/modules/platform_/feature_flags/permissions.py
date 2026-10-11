"""Feature flag permission codes (platform-admin read-only in Phase 3)."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_FEATURE_FLAG_LIST = registry.register(
    "platform", "feature_flag", Action.LIST, "List feature flags"
)
