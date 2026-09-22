"""API v1 aggregate router. Each module owns its sub-router and permissions."""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.academic.academic_classes.router import router as academic_classes_router
from app.modules.academic.academic_terms.router import router as academic_terms_router
from app.modules.academic.academic_years.router import router as academic_years_router
from app.modules.academic.class_subjects.router import router as class_subjects_router
from app.modules.academic.cohorts.router import router as cohorts_router
from app.modules.academic.subjects.router import router as subjects_router
from app.modules.auth.router import router as auth_router
from app.modules.iam.memberships.router import router as memberships_router
from app.modules.iam.organizations.router import router as organizations_router
from app.modules.iam.roles.router import router as roles_router
from app.modules.iam.schools.router import router as schools_router
from app.modules.iam.users.router import router as users_router
from app.modules.people.addresses.router import router as addresses_router
from app.modules.people.contacts.router import router as contacts_router
from app.modules.people.persons.router import router as persons_router
from app.modules.platform_.audit.router import router as audit_logs_router
from app.modules.platform_.stats.router import router as platform_stats_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(audit_logs_router)
api_router.include_router(platform_stats_router)
api_router.include_router(organizations_router)
api_router.include_router(schools_router)
api_router.include_router(users_router)
api_router.include_router(memberships_router)
api_router.include_router(roles_router)
api_router.include_router(persons_router)
api_router.include_router(addresses_router)
api_router.include_router(contacts_router)
api_router.include_router(academic_years_router)
api_router.include_router(academic_terms_router)
api_router.include_router(academic_classes_router)
api_router.include_router(subjects_router)
api_router.include_router(class_subjects_router)
api_router.include_router(cohorts_router)
