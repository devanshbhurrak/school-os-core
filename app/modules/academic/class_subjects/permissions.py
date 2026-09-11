"""ClassSubject permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_CLASS_SUBJECT_LIST = registry.register("academic", "class_subject", Action.LIST, "List class subjects")
P_CLASS_SUBJECT_READ = registry.register("academic", "class_subject", Action.READ, "View a class subject")
P_CLASS_SUBJECT_CREATE = registry.register("academic", "class_subject", Action.CREATE, "Create a class subject")
P_CLASS_SUBJECT_DELETE = registry.register("academic", "class_subject", Action.DELETE, "Delete a class subject")
