"""Shared test setup. Registers the permission catalog so `registry` is
populated even for unit tests that never import the app."""
from __future__ import annotations

from app.modules.academic.academic_classes import permissions as _acl_p  # noqa: F401
from app.modules.academic.academic_terms import permissions as _at_p  # noqa: F401
from app.modules.academic.academic_years import permissions as _ay_p  # noqa: F401
from app.modules.academic.class_subjects import permissions as _cs_p  # noqa: F401
from app.modules.academic.cohorts import permissions as _coh_p  # noqa: F401
from app.modules.academic.subjects import permissions as _sub_p  # noqa: F401

# Importing these modules populates app.core.permissions.registry.
from app.modules.iam.memberships import permissions as _mp  # noqa: F401
from app.modules.iam.organizations import permissions as _op  # noqa: F401
from app.modules.iam.roles import permissions as _rp  # noqa: F401
from app.modules.iam.schools import permissions as _sp  # noqa: F401
from app.modules.iam.users import permissions as _up  # noqa: F401
from app.modules.people.addresses import permissions as _ap  # noqa: F401
from app.modules.people.contacts import permissions as _cp  # noqa: F401
from app.modules.people.persons import permissions as _pp  # noqa: F401
from app.modules.platform_.audit import permissions as _audit_p  # noqa: F401
