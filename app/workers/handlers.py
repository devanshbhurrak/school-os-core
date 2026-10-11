"""Outbox event handlers — map event types to notification fan-out.

Each handler receives its own transaction (`session` already begun by the
dispatcher) and must be idempotent: the dispatcher retries on failure, and
`InAppChannel` dedupes per (user, entity, type).

Event contract (payloads written by domain services):
* `ANNOUNCEMENT_PUBLISHED` — {announcement_id, title, priority, targets[]}
* `ATTENDANCE_SUBMITTED` — {session_id, cohort_id, session_date}
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.iam.enums import MembershipStatus
from app.modules.iam.models import Membership, User
from app.workers.channels import ChannelMessage, ChannelRegistry

logger = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, dict[str, Any], ChannelRegistry, dict[str, Any]], Awaitable[int]]
# Handler signature: (session, payload, channels, envelope) -> recipients count.
# envelope carries {event_id, event_name, organization_id, school_id}.


async def _active_user_ids_in_school(
    session: AsyncSession, organization_id: str, school_id: str
) -> list[str]:
    """Users with ACTIVE memberships covering `school_id` (direct or org-wide)."""
    stmt = (
        select(distinct(Membership.user_id))
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.organization_id == organization_id,
            Membership.status == MembershipStatus.ACTIVE.value,
            User.status == "ACTIVE",
            User.deleted_at.is_(None),
            ((Membership.school_id == school_id) | (Membership.school_id.is_(None))),
        )
    )
    return list((await session.scalars(stmt)).all())


async def _user_ids_with_role_codes(
    session: AsyncSession,
    organization_id: str,
    school_id: str,
    role_codes: set[str],
) -> list[str]:
    """Narrow school members to those holding any of `role_codes`."""
    from app.modules.iam.models import MembershipRole, Role

    stmt = (
        select(distinct(Membership.user_id))
        .join(User, User.id == Membership.user_id)
        .join(MembershipRole, MembershipRole.membership_id == Membership.id)
        .join(Role, Role.id == MembershipRole.role_id)
        .where(
            Membership.organization_id == organization_id,
            Membership.status == MembershipStatus.ACTIVE.value,
            User.status == "ACTIVE",
            User.deleted_at.is_(None),
            Role.code.in_(role_codes),
            ((Membership.school_id == school_id) | (Membership.school_id.is_(None))),
        )
    )
    return list((await session.scalars(stmt)).all())


async def handle_announcement_published(
    session: AsyncSession,
    payload: dict[str, Any],
    channels: ChannelRegistry,
    envelope: dict[str, Any],
) -> int:
    org_id = envelope.get("organization_id")
    school_id = envelope.get("school_id")
    if not org_id or not school_id:
        logger.warning("announcement_event_missing_tenant", extra={"event_id": envelope.get("event_id")})
        return 0

    targets: list[dict[str, Any]] = payload.get("targets") or []
    role_targets = {
        str(t.get("target_id")).upper()
        for t in targets
        if str(t.get("target_type")).upper() == "ROLE" and t.get("target_id")
    }
    if role_targets:
        user_ids = await _user_ids_with_role_codes(session, org_id, school_id, role_targets)
    else:
        # SCHOOL/CLASS/COHORT/untargeted → all active school members.
        user_ids = await _active_user_ids_in_school(session, org_id, school_id)

    title = str(payload.get("title") or "New announcement")
    announcement_id = payload.get("announcement_id")
    for user_id in user_ids:
        await channels.broadcast(
            session,
            ChannelMessage(
                user_id=user_id,
                organization_id=org_id,
                school_id=school_id,
                type="ANNOUNCEMENT",
                title=title,
                body=f"Priority: {payload.get('priority', 'NORMAL')}",
                entity_type="announcement",
                entity_id=announcement_id,
                dedupe_key=f"ANNOUNCEMENT_PUBLISHED:{envelope.get('event_id')}:{user_id}",
            ),
        )
    return len(user_ids)


async def handle_attendance_submitted(
    session: AsyncSession,
    payload: dict[str, Any],
    channels: ChannelRegistry,
    envelope: dict[str, Any],
) -> int:
    """Notify parents/guardians of students recorded in the session."""
    from app.modules.attendance.models import AttendanceRecord
    from app.modules.iam.models import User as UserModel
    from app.modules.parents.models import Parent, StudentParent

    org_id = envelope.get("organization_id")
    school_id = envelope.get("school_id")
    session_id = payload.get("session_id") or envelope.get("entity_id")
    if not org_id or not school_id or not session_id:
        logger.warning("attendance_event_missing_refs", extra={"event_id": envelope.get("event_id")})
        return 0

    student_ids = list(
        (await session.scalars(
            select(distinct(AttendanceRecord.student_id)).where(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.school_id == school_id,
            )
        )).all()
    )
    if not student_ids:
        return 0

    # StudentParent -> Parent.person_id -> User.person_id (active accounts).
    parent_person_ids = list(
        (await session.scalars(
            select(distinct(Parent.person_id))
            .join(StudentParent, StudentParent.parent_id == Parent.id)
            .where(
                StudentParent.student_id.in_(student_ids),
                StudentParent.school_id == school_id,
                Parent.deleted_at.is_(None),
            )
        )).all()
    )
    if not parent_person_ids:
        return 0

    parent_user_ids = list(
        (await session.scalars(
            select(UserModel.id).where(
                UserModel.person_id.in_(parent_person_ids),
                UserModel.status == "ACTIVE",
                UserModel.deleted_at.is_(None),
            )
        )).all()
    )

    date_label = payload.get("session_date") or ""
    for user_id in parent_user_ids:
        await channels.broadcast(
            session,
            ChannelMessage(
                user_id=user_id,
                organization_id=org_id,
                school_id=school_id,
                type="ATTENDANCE",
                title=f"Attendance submitted{f' for {date_label}' if date_label else ''}",
                body="Your child's attendance has been recorded.",
                entity_type="attendance_session",
                entity_id=session_id,
                dedupe_key=f"ATTENDANCE_SUBMITTED:{envelope.get('event_id')}:{user_id}",
            ),
        )
    return len(parent_user_ids)


HANDLERS: dict[str, Handler] = {
    "ANNOUNCEMENT_PUBLISHED": handle_announcement_published,
    "ATTENDANCE_SUBMITTED": handle_attendance_submitted,
}
