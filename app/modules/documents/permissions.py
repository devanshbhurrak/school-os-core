"""Document permission codes."""
from __future__ import annotations

from app.core.permissions import Action, registry

P_DOCUMENT_LIST = registry.register("documents", "document", Action.LIST, "List documents")
P_DOCUMENT_READ = registry.register("documents", "document", Action.READ, "View a document")
P_DOCUMENT_CREATE = registry.register("documents", "document", Action.CREATE, "Upload a document")
P_DOCUMENT_DELETE = registry.register("documents", "document", Action.DELETE, "Delete a document")
