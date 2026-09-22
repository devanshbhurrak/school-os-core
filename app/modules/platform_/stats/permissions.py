"""Platform stats permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_PLATFORM_STATS_READ = registry.register(
    "platform", "stats", Action.READ, "Read platform-wide aggregate statistics"
)
