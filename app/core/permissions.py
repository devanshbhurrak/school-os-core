"""Permission registry and data-scope model.

A permission answers *which action*; a `DataScope` answers *which rows*. Both
are required, and conflating them forces per-endpoint row filters later.

Permissions are declared once, in code, via `registry.register(...)`. The
database mirror is kept in sync by `scripts/sync_permissions.py`. `require()`
in `app/core/authz.py` validates codes against the registry at import time, so
a typo is a startup crash rather than a silent 403 in production.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, StrEnum


class Action(StrEnum):
    LIST = "list"
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ARCHIVE = "archive"
    EXPORT = "export"


class DataScope(str, Enum):  # noqa: UP042
    """Row-visibility tier. OWN < ASSIGNED < SCHOOL < ORGANIZATION < PLATFORM."""

    OWN = "OWN"
    ASSIGNED = "ASSIGNED"
    SCHOOL = "SCHOOL"
    ORGANIZATION = "ORGANIZATION"
    PLATFORM = "PLATFORM"

    # NOTE: must be a list — Python 3.13 misreads a tuple of strings here.
    _ORDER = ["OWN", "ASSIGNED", "SCHOOL", "ORGANIZATION", "PLATFORM"]

    def strength(self) -> int:
        return self._ORDER.index(self.value)

    @classmethod
    def strongest(cls, scopes: set[DataScope]) -> DataScope | None:
        if not scopes:
            return None
        return max(scopes, key=lambda s: s.strength())


_CODE_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$")


@dataclass(frozen=True, slots=True)
class Permission:
    code: str  # "students.student.read"
    module: str
    resource: str
    action: str
    description: str


class PermissionRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, Permission] = {}

    def register(
        self,
        module: str,
        resource: str,
        action: str | Action,
        description: str,
    ) -> Permission:
        action_value = action.value if isinstance(action, Action) else action
        code = f"{module}.{resource}.{action_value}"
        if not _CODE_RE.match(code):
            raise ValueError(f"Invalid permission code format: {code!r}")
        if code in self._registry:
            raise ValueError(f"Duplicate permission code: {code}")
        permission = Permission(
            code=code,
            module=module,
            resource=resource,
            action=action_value,
            description=description,
        )
        self._registry[code] = permission
        return permission

    def get(self, code: str) -> Permission | None:
        return self._registry.get(code)

    def require_registered(self, code: str) -> Permission:
        """Raise if a route references an unregistered code (startup crash)."""
        permission = self._registry.get(code)
        if permission is None:
            raise RuntimeError(
                f"Permission {code!r} is not registered. "
                "Declare it in the owning module's permissions.py."
            )
        return permission

    def validate_all(self) -> None:
        """Format sanity check for every registered permission. Called at startup."""
        for code in self._registry:
            if not _CODE_RE.match(code):
                raise ValueError(f"Invalid permission code: {code!r}")

    def all(self) -> list[Permission]:
        return list(self._registry.values())


registry = PermissionRegistry()
