"""Bulk import/export permissions."""
from __future__ import annotations

from app.core.permissions import Action, registry

IMPORT_LIST = registry.register("bulk_import", "import", Action.LIST, "List import jobs")
IMPORT_READ = registry.register("bulk_import", "import", Action.READ, "Read import job details")
IMPORT_CREATE = registry.register("bulk_import", "import", Action.CREATE, "Upload CSV for bulk import")
EXPORT_CREATE = registry.register("bulk_import", "export", Action.CREATE, "Export records as CSV")
