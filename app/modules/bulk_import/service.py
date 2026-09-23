"""Bulk import/export business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import InvalidRequestError
from app.db.types import gen_ulid
from app.modules.bulk_import import repository
from app.modules.bulk_import.csv_helpers import (
    STUDENT_COLUMNS,
    TEACHER_COLUMNS,
    generate_student_csv,
    generate_teacher_csv,
    parse_csv,
    validate_student_row,
    validate_teacher_row,
)
from app.modules.bulk_import.enums import ImportJobStatus, ImportResourceType
from app.modules.bulk_import.models import ImportJob
from app.modules.people.models import Person
from app.modules.people.persons.schemas import PersonCreate
from app.modules.students.models import Student
from app.modules.students.schemas import StudentCreate
from app.modules.teachers.models import Teacher
from app.modules.teachers.schemas import TeacherCreate


async def start_import(
    session: AsyncSession,
    ctx: RequestContext,
    resource_type: ImportResourceType,
    file_content: bytes,
    filename: str,
) -> ImportJob:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    # Parse CSV
    try:
        rows = parse_csv(file_content)
    except ValueError as exc:
        # Create a FAILED job immediately
        job = await repository.create_job(session, {
            "id": gen_ulid(),
            "school_id": ctx.school_id,
            "organization_id": ctx.organization_id,
            "resource_type": resource_type.value,
            "status": ImportJobStatus.FAILED.value,
            "total_rows": 0,
            "processed_rows": 0,
            "success_rows": 0,
            "failed_rows": 0,
            "error_summary": [{"row": 0, "field": "file", "message": str(exc)}],
            "original_filename": filename,
            "started_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
            "created_by_id": ctx.user_id,
        })
        return job

    if not rows:
        job = await repository.create_job(session, {
            "id": gen_ulid(),
            "school_id": ctx.school_id,
            "organization_id": ctx.organization_id,
            "resource_type": resource_type.value,
            "status": ImportJobStatus.FAILED.value,
            "total_rows": 0,
            "processed_rows": 0,
            "success_rows": 0,
            "failed_rows": 0,
            "error_summary": [{"row": 0, "field": "file", "message": "CSV file is empty or has no data rows"}],
            "original_filename": filename,
            "started_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
            "created_by_id": ctx.user_id,
        })
        return job

    # Validate all rows upfront
    all_errors: list[dict] = []
    if resource_type == ImportResourceType.STUDENTS:
        for i, row in enumerate(rows, start=2):  # row 1 = header
            _, row_errors = validate_student_row(row, i)
            all_errors.extend(row_errors)
    else:
        for i, row in enumerate(rows, start=2):
            _, row_errors = validate_teacher_row(row, i)
            all_errors.extend(row_errors)

    # Create job with PROCESSING status
    job = await repository.create_job(session, {
        "id": gen_ulid(),
        "school_id": ctx.school_id,
        "organization_id": ctx.organization_id,
        "resource_type": resource_type.value,
        "status": ImportJobStatus.PROCESSING.value,
        "total_rows": len(rows),
        "processed_rows": 0,
        "success_rows": 0,
        "failed_rows": len(all_errors) if all_errors else 0,
        "error_summary": all_errors if all_errors else None,
        "original_filename": filename,
        "started_at": datetime.now(UTC),
        "created_by_id": ctx.user_id,
    })

    success_rows = 0
    failed_rows = 0
    row_errors: list[dict] = list(all_errors)

    # Process each row
    for i, row in enumerate(rows, start=2):
        if resource_type == ImportResourceType.STUDENTS:
            is_valid, _ = validate_student_row(row, i)
        else:
            is_valid, _ = validate_teacher_row(row, i)

        if not is_valid:
            failed_rows += 1
            continue

        try:
            # Create person first
            person_data = PersonCreate(
                first_name=row.get("first_name", ""),
                last_name=row.get("last_name") or None,
                primary_email=row.get("primary_email") or None,
                primary_phone=row.get("primary_phone") or None,
            )
            person = Person(
                organization_id=ctx.organization_id,
                created_by_id=ctx.user_id,
                **person_data.model_dump(),
            )
            session.add(person)
            await session.flush()

            if resource_type == ImportResourceType.STUDENTS:
                from datetime import date as date_type
                student_data = StudentCreate(
                    person_id=person.id,
                    admission_number=row["admission_number"].strip(),
                    admission_date=date_type.fromisoformat(row["admission_date"].strip()),
                    status=row.get("status", "").strip() or "ACTIVE",
                )
                student = Student(
                    school_id=ctx.school_id,
                    organization_id=ctx.organization_id,
                    created_by_id=ctx.user_id,
                    **student_data.model_dump(),
                )
                session.add(student)
                await session.flush()
            else:
                from datetime import date as date_type
                joining_date_str = row.get("joining_date", "").strip()
                teacher_data = TeacherCreate(
                    person_id=person.id,
                    employee_number=row.get("employee_number") or None,
                    designation=row.get("designation") or None,
                    joining_date=date_type.fromisoformat(joining_date_str) if joining_date_str else None,
                    status=row.get("status", "").strip() or "ACTIVE",
                )
                teacher = Teacher(
                    school_id=ctx.school_id,
                    organization_id=ctx.organization_id,
                    created_by_id=ctx.user_id,
                    **teacher_data.model_dump(),
                )
                session.add(teacher)
                await session.flush()

            success_rows += 1
        except Exception as exc:
            failed_rows += 1
            row_errors.append({"row": i, "field": "row", "message": str(exc)})

    # Determine final status
    if failed_rows == 0:
        final_status = ImportJobStatus.COMPLETED
    elif success_rows > 0:
        final_status = ImportJobStatus.PARTIAL
    else:
        final_status = ImportJobStatus.FAILED

    job = await repository.update_job(session, job, {
        "status": final_status.value,
        "processed_rows": success_rows + failed_rows,
        "success_rows": success_rows,
        "failed_rows": failed_rows,
        "error_summary": row_errors if row_errors else None,
        "completed_at": datetime.now(UTC),
    })
    return job


async def get_export(
    session: AsyncSession,
    ctx: RequestContext,
    resource_type: ImportResourceType,
) -> bytes:
    if ctx.school_id is None:
        raise InvalidRequestError("No school context is set for this request.")

    if resource_type == ImportResourceType.STUDENTS:
        stmt = (
            select(Student, Person)
            .join(Person, Student.person_id == Person.id)
            .where(
                Student.school_id == ctx.school_id,
                Student.deleted_at.is_(None),
            )
        )
        results = (await session.execute(stmt)).all()
        rows = [
            {
                "first_name": person.first_name,
                "last_name": person.last_name or "",
                "primary_email": person.primary_email or "",
                "primary_phone": person.primary_phone or "",
                "admission_number": student.admission_number,
                "admission_date": str(student.admission_date) if student.admission_date else "",
                "status": student.status,
            }
            for student, person in results
        ]
        return generate_student_csv(rows)
    else:
        stmt = (
            select(Teacher, Person)
            .join(Person, Teacher.person_id == Person.id)
            .where(
                Teacher.school_id == ctx.school_id,
                Teacher.deleted_at.is_(None),
            )
        )
        results = (await session.execute(stmt)).all()
        rows = [
            {
                "first_name": person.first_name,
                "last_name": person.last_name or "",
                "primary_email": person.primary_email or "",
                "primary_phone": person.primary_phone or "",
                "employee_number": teacher.employee_number or "",
                "designation": teacher.designation or "",
                "joining_date": str(teacher.joining_date) if teacher.joining_date else "",
                "status": teacher.status,
            }
            for teacher, person in results
        ]
        return generate_teacher_csv(rows)
