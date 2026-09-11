"""Unit tests for the permission registry."""
from __future__ import annotations

import pytest

from app.core.permissions import Action, PermissionRegistry, registry


def test_register_and_get() -> None:
    local = PermissionRegistry()
    permission = local.register("tests", "widget", Action.READ, "Read a widget")
    assert permission.code == "tests.widget.read"
    assert local.get("tests.widget.read") is permission


def test_duplicate_registration_rejected() -> None:
    local = PermissionRegistry()
    local.register("tests", "widget", Action.READ, "Read a widget")
    with pytest.raises(ValueError):
        local.register("tests", "widget", Action.READ, "Read a widget again")


def test_invalid_code_format_rejected() -> None:
    local = PermissionRegistry()
    with pytest.raises(ValueError):
        local.register("invalid module", "widget", "read", "x")


def test_require_registered_raises_for_unknown() -> None:
    local = PermissionRegistry()
    with pytest.raises(RuntimeError):
        local.require_registered("iam.ghost.read")


def test_global_registry_is_valid() -> None:
    registry.validate_all()
    for permission in registry.all():
        assert permission.code.startswith(f"{permission.module}.{permission.resource}.")
