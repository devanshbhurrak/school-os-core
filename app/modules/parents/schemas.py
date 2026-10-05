"""Parent request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.parents.enums import ParentRelationship, ParentStatus


class ParentCreate(BaseModel):
    person_id: str
    occupation: str | None = Field(default=None, max_length=200)
    workplace: str | None = Field(default=None, max_length=200)


class ParentUpdate(BaseModel):
    occupation: str | None = Field(default=None, max_length=200)
    workplace: str | None = Field(default=None, max_length=200)
    status: ParentStatus | None = None
    version: int = Field(ge=1)


class ParentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    person_id: str
    occupation: str | None
    workplace: str | None
    status: ParentStatus
    version: int
    created_at: datetime
    updated_at: datetime

    # Denormalized from Person relationship
    first_name: str = ""
    last_name: str | None = None
    primary_email: str | None = None
    primary_phone: str | None = None

    @classmethod
    def from_orm_with_person(cls, parent: object) -> "ParentRead":
        person = getattr(parent, "person", None)
        data = cls.model_validate(parent)
        if person is not None:
            data.first_name = getattr(person, "first_name", "")
            data.last_name = getattr(person, "last_name", None)
            data.primary_email = getattr(person, "primary_email", None)
            data.primary_phone = getattr(person, "primary_phone", None)
        return data


class StudentParentCreate(BaseModel):
    parent_id: str
    relationship: ParentRelationship
    is_primary: bool = False
    is_emergency_contact: bool = False
    can_pickup: bool = True


class StudentParentUpdate(BaseModel):
    relationship: ParentRelationship | None = None
    is_primary: bool | None = None
    is_emergency_contact: bool | None = None
    can_pickup: bool | None = None


class StudentParentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    parent_id: str
    relationship: str
    is_primary: bool
    is_emergency_contact: bool
    can_pickup: bool
    created_at: datetime

    # Denormalized from Parent -> Person
    first_name: str = ""
    last_name: str | None = None
    primary_email: str | None = None
    primary_phone: str | None = None
    occupation: str | None = None
    workplace: str | None = None

    @classmethod
    def from_orm_with_parent(cls, link: object) -> "StudentParentRead":
        data = cls.model_validate(link)
        parent = getattr(link, "parent", None)
        if parent is not None:
            data.occupation = getattr(parent, "occupation", None)
            data.workplace = getattr(parent, "workplace", None)
            person = getattr(parent, "person", None)
            if person is not None:
                data.first_name = getattr(person, "first_name", "")
                data.last_name = getattr(person, "last_name", None)
                data.primary_email = getattr(person, "primary_email", None)
                data.primary_phone = getattr(person, "primary_phone", None)
        return data
