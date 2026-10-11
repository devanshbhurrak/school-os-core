"""0026 — race-proof assignment conflict indexes (Phase 3, C2).

The app-level `check_assignment_conflict` has a check-then-insert race under
concurrent writers. These partial unique indexes make the database the
arbiter; services map the resulting IntegrityError to 409 ASSIGNMENT_CONFLICT.
"""
from __future__ import annotations

from alembic import op

revision = "0026_assignment_conflict_indexes"
down_revision = "0025_outbox_dispatch_claim"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_assignment_class_teacher_active
        ON teacher_assignments (school_id, cohort_id, academic_year_id)
        WHERE role = 'CLASS_TEACHER' AND status = 'ACTIVE'
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_assignment_subject_teacher_active
        ON teacher_assignments (school_id, cohort_id, subject_id, academic_year_id)
        WHERE role = 'SUBJECT_TEACHER' AND status = 'ACTIVE'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_assignment_subject_teacher_active")
    op.execute("DROP INDEX IF EXISTS uq_assignment_class_teacher_active")
