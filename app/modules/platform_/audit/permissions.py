"""Audit log permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_AUDIT_LOG_LIST = registry.register("platform", "audit_log", Action.LIST, "List audit logs")
P_AUDIT_LOG_READ = registry.register("platform", "audit_log", Action.READ, "View an audit log")
