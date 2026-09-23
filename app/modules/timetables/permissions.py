"""Timetable permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

PERIOD_LIST = registry.register("timetables", "period", Action.LIST, "List period definitions")
PERIOD_READ = registry.register("timetables", "period", Action.READ, "View a period definition")
PERIOD_CREATE = registry.register("timetables", "period", Action.CREATE, "Create a period definition")
PERIOD_UPDATE = registry.register("timetables", "period", Action.UPDATE, "Update a period definition")
PERIOD_DELETE = registry.register("timetables", "period", Action.DELETE, "Delete a period definition")

SLOT_LIST = registry.register("timetables", "slot", Action.LIST, "List timetable slots")
SLOT_READ = registry.register("timetables", "slot", Action.READ, "View a timetable slot")
SLOT_CREATE = registry.register("timetables", "slot", Action.CREATE, "Create a timetable slot")
SLOT_UPDATE = registry.register("timetables", "slot", Action.UPDATE, "Update a timetable slot")
SLOT_DELETE = registry.register("timetables", "slot", Action.DELETE, "Cancel a timetable slot")
