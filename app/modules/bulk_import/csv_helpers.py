"""Pure CSV utility functions — no DB calls."""
from __future__ import annotations

import csv
import io
from datetime import date

STUDENT_COLUMNS = [
    "first_name",       # required
    "last_name",        # optional
    "primary_email",    # optional
    "primary_phone",    # optional
    "admission_number", # required
    "admission_date",   # required, YYYY-MM-DD
    "status",           # optional, default ACTIVE
]

TEACHER_COLUMNS = [
    "first_name",       # required
    "last_name",        # optional
    "primary_email",    # optional
    "primary_phone",    # optional
    "employee_number",  # optional
    "designation",      # optional
    "joining_date",     # optional, YYYY-MM-DD
    "status",           # optional, default ACTIVE
]

_VALID_STUDENT_STATUSES = {"ACTIVE", "WITHDRAWN", "GRADUATED", "TRANSFERRED", "INACTIVE", "DECEASED"}
_VALID_TEACHER_STATUSES = {"ACTIVE", "INACTIVE", "ON_LEAVE", "RESIGNED", "TERMINATED"}


def parse_csv(content: bytes) -> list[dict]:
    """Parse CSV bytes into a list of row dicts. Raises ValueError on malformed CSV."""
    try:
        text = content.decode("utf-8-sig")  # strip BOM if present
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            # Strip whitespace from keys and values
            rows.append({k.strip(): (v.strip() if v else v) for k, v in row.items()})
        return rows
    except Exception as exc:
        raise ValueError(f"Failed to parse CSV: {exc}") from exc


def validate_student_row(row: dict, row_num: int) -> tuple[bool, list[dict]]:
    """Validate a student CSV row. Returns (is_valid, errors)."""
    errors: list[dict] = []

    if not row.get("first_name"):
        errors.append({"row": row_num, "field": "first_name", "message": "first_name is required"})

    if not row.get("admission_number"):
        errors.append({"row": row_num, "field": "admission_number", "message": "admission_number is required"})

    if not row.get("admission_date"):
        errors.append({"row": row_num, "field": "admission_date", "message": "admission_date is required"})
    else:
        try:
            date.fromisoformat(row["admission_date"])
        except ValueError:
            errors.append({
                "row": row_num,
                "field": "admission_date",
                "message": "admission_date must be YYYY-MM-DD format",
            })

    status = row.get("status", "").strip()
    if status and status not in _VALID_STUDENT_STATUSES:
        errors.append({
            "row": row_num,
            "field": "status",
            "message": f"status must be one of {sorted(_VALID_STUDENT_STATUSES)}",
        })

    return len(errors) == 0, errors


def validate_teacher_row(row: dict, row_num: int) -> tuple[bool, list[dict]]:
    """Validate a teacher CSV row. Returns (is_valid, errors)."""
    errors: list[dict] = []

    if not row.get("first_name"):
        errors.append({"row": row_num, "field": "first_name", "message": "first_name is required"})

    joining_date = row.get("joining_date", "").strip()
    if joining_date:
        try:
            date.fromisoformat(joining_date)
        except ValueError:
            errors.append({
                "row": row_num,
                "field": "joining_date",
                "message": "joining_date must be YYYY-MM-DD format",
            })

    status = row.get("status", "").strip()
    if status and status not in _VALID_TEACHER_STATUSES:
        errors.append({
            "row": row_num,
            "field": "status",
            "message": f"status must be one of {sorted(_VALID_TEACHER_STATUSES)}",
        })

    return len(errors) == 0, errors


def generate_student_csv(students: list[dict]) -> bytes:
    """Generate CSV bytes from a list of student dicts."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=STUDENT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(students)
    return output.getvalue().encode("utf-8")


def generate_teacher_csv(teachers: list[dict]) -> bytes:
    """Generate CSV bytes from a list of teacher dicts."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TEACHER_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(teachers)
    return output.getvalue().encode("utf-8")
