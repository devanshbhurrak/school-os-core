"""Unit tests for data-scope ordering and the authorization guard factory."""
from __future__ import annotations

import pytest

from app.core.authz import require
from app.core.permissions import DataScope, Permission, registry


def test_data_scope_strength_ordering() -> None:
    assert DataScope.OWN.strength() < DataScope.ASSIGNED.strength()
    assert DataScope.ASSIGNED.strength() < DataScope.SCHOOL.strength()
    assert DataScope.SCHOOL.strength() < DataScope.ORGANIZATION.strength()
    assert DataScope.ORGANIZATION.strength() < DataScope.PLATFORM.strength()


def test_strongest() -> None:
    assert DataScope.strongest({DataScope.SCHOOL, DataScope.OWN}) == DataScope.SCHOOL
    assert DataScope.strongest(set()) is None


def test_require_rejects_unregistered_code_at_import_time() -> None:
    phantom = Permission("ghost.module.read", "ghost", "module", "read", "x")
    with pytest.raises(RuntimeError):
        require(phantom)


def test_require_accepts_registered_code() -> None:
    guard = require(registry.all()[0])
    assert callable(guard)
