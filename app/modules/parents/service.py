"""Parent business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError, StaleResourceError
from app.modules.parents import repository
from app.modules.parents.models import Parent, StudentParent
from app.modules.parents.schemas import ParentCreate, ParentUpdate, StudentParentCreate
from app.modules.people.models import Person
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["occupation", "workplace", "status"]


def _parent_snapshot(parent: Parent) -> dict:
    return snapshot(parent, _SNAPSHOT_FIELDS)


async def create(session: AsyncSession, ctx: RequestContext, data: ParentCreate) -> Parent:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Validate person exists in this organization
    person = await session.scalar(
        select(Person).where(
            Person.id == data.person_id,
            Person.organization_id == ctx.organization_id,
            Person.deleted_at.is_(None),
        )
    )
    if person is None:
        raise NotFoundError(
            "The specified person does not exist in this organization.",
            code="PERSON_NOT_FOUND",
        )

    # Check no duplicate parent for same person+school
    if await repository.get_by_person_id(session, ctx.school_id, data.person_id):
        raise ConflictError(
            "This person is already registered as a parent at this school.",
            code="PERSON_ALREADY_PARENT",
            details={"person_id": data.person_id},
        )

    instance = Parent(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    session.add(instance)
    await session.flush()

    instance.person = person  # type: ignore[assignment]

    await audit(
        session, ctx,
        action="PARENT_CREATED",
        entity_type="parent",
        entity_id=instance.id,
        summary=f"Parent record created for person {data.person_id!r}",
        after=_parent_snapshot(instance),
    )
    return instance


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    parent: Parent,
    data: ParentUpdate,
) -> Parent:
    if parent.version != data.version:
        raise StaleResourceError()

    before = _parent_snapshot(parent)
    payload = data.model_dump(exclude={"version"}, exclude_none=True)
    for field, value in payload.items():
        setattr(parent, field, value)
    parent.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="PARENT_UPDATED",
        entity_type="parent",
        entity_id=parent.id,
        summary=f"Parent {parent.id!r} updated",
        before=before,
        after=_parent_snapshot(parent),
    )
    return parent


async def delete(session: AsyncSession, ctx: RequestContext, parent: Parent, version: int) -> None:
    if parent.version != version:
        raise StaleResourceError()

    before = _parent_snapshot(parent)
    parent.deleted_at = datetime.now(UTC)
    parent.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="PARENT_DELETED",
        entity_type="parent",
        entity_id=parent.id,
        summary=f"Parent {parent.id!r} deleted",
        before=before,
    )


async def get(session: AsyncSession, ctx: RequestContext, parent_id: str) -> Parent:
    if ctx.school_id is None:
        raise NotFoundError("The parent was not found.", code="PARENT_NOT_FOUND")
    obj = await repository.get_by_id(session, ctx.school_id, parent_id)
    if obj is None:
        raise NotFoundError("The parent was not found.", code="PARENT_NOT_FOUND")
    return obj


async def list_parents(session: AsyncSession, ctx: RequestContext, params, *, search=None, status=None):
    if ctx.school_id is None:
        from app.core.pagination import CursorPage
        return CursorPage(items=[], next_cursor=None, has_more=False)
    return await repository.list_parents(session, ctx.school_id, params, search=search, status=status)


async def list_children(session: AsyncSession, ctx: RequestContext, parent_id: str):
    if ctx.school_id is None:
        return []
    # Validate parent exists
    await get(session, ctx, parent_id)
    return await repository.list_children(session, parent_id, ctx.school_id)


async def link_to_student(
    session: AsyncSession, ctx: RequestContext, student_id: str, data: StudentParentCreate
) -> StudentParent:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Validate parent exists
    parent = await repository.get_by_id(session, ctx.school_id, data.parent_id)
    if parent is None:
        raise NotFoundError("The parent was not found.", code="PARENT_NOT_FOUND")

    # Validate student exists
    from app.modules.students import repository as student_repo
    student = await student_repo.get_by_id(session, ctx.school_id, student_id)
    if student is None:
        raise NotFoundError("The student was not found.", code="STUDENT_NOT_FOUND")

    # Check duplicate
    if await repository.get_student_parent_by_pair(session, student_id, data.parent_id):
        raise ConflictError(
            "This parent is already linked to this student.",
            code="PARENT_ALREADY_LINKED",
            details={"student_id": student_id, "parent_id": data.parent_id},
        )

    link = StudentParent(
        school_id=ctx.school_id,
        organization_id=ctx.organization_id,
        student_id=student_id,
        parent_id=data.parent_id,
        relationship=data.relationship.value,
        is_primary=data.is_primary,
        is_emergency_contact=data.is_emergency_contact,
        can_pickup=data.can_pickup,
        created_by_id=ctx.user_id,
    )
    session.add(link)
    await session.flush()

    await audit(
        session, ctx,
        action="STUDENT_PARENT_LINKED",
        entity_type="student_parent",
        entity_id=link.id,
        summary=f"Parent {data.parent_id!r} linked to student {student_id!r}",
        after={"student_id": student_id, "parent_id": data.parent_id, "relationship": data.relationship.value},
    )

    # Reload with relationships
    loaded = await repository.get_student_parent(session, link.id, ctx.school_id)
    return loaded or link


async def unlink_from_student(session: AsyncSession, ctx: RequestContext, link_id: str) -> None:
    if ctx.school_id is None:
        raise NotFoundError("Link not found.", code="STUDENT_PARENT_NOT_FOUND")

    link = await repository.get_student_parent(session, link_id, ctx.school_id)
    if link is None:
        raise NotFoundError("Link not found.", code="STUDENT_PARENT_NOT_FOUND")

    before = {
        "student_id": link.student_id,
        "parent_id": link.parent_id,
        "relationship": link.relationship,
    }
    await session.delete(link)
    await session.flush()

    await audit(
        session, ctx,
        action="STUDENT_PARENT_UNLINKED",
        entity_type="student_parent",
        entity_id=link_id,
        summary=f"Parent {link.parent_id!r} unlinked from student {link.student_id!r}",
        before=before,
    )


async def list_parents_for_student(session: AsyncSession, ctx: RequestContext, student_id: str):
    if ctx.school_id is None:
        return []
    return await repository.list_parents_for_student(session, student_id, ctx.school_id)
