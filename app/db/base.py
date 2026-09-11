"""SQLAlchemy declarative base for all ORM models."""
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# CHECK constraints are declared with short names (the enum column or rule)
# and wrapped into the standard `ck_<table>_<name>` form by this convention,
# matching the names the migrations emit via `op.f(...)`. `index=True`
# columns become unnamed `Index` objects, which the `ix` convention names
# `ix_<table>_<column>` — again matching the migrations. All explicitly named
# constraints keep their names verbatim (`%(constraint_name)s` is not in those
# templates, so the convention never rewrites them).
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)
