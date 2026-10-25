"""Instructor request/response schemas — doc 08 §2.14."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Shared sub-objects ────────────────────────────────────────────────────────

class InstructorAssignedCourse(BaseModel):
    """Course summary nested in instructor detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    thumbnail_url: str | None = None
    status: str
    enrolled_count: int = 0


class InstructorOption(BaseModel):
    """Lightweight item for dropdown — GET /api/instructors/options (§2.14f)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    title: str
    avatar_url: str | None = None


# ── List (admin) ──────────────────────────────────────────────────────────────

class AdminInstructorItem(BaseModel):
    """Row in paginated admin list — §2.14a."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    title: str
    email: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    courses_count: int = 0
    is_active: bool
    created_at: datetime


class AdminInstructorListResponse(BaseModel):
    """Paginated response for GET /api/admin/instructors."""

    data: list[AdminInstructorItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Detail (admin) ────────────────────────────────────────────────────────────

class AdminInstructorDetail(BaseModel):
    """Full instructor detail — §2.14b."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    title: str
    bio: str | None = None
    avatar_url: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool
    courses: list[InstructorAssignedCourse] = []
    created_at: datetime
    updated_at: datetime


# ── Delete response ───────────────────────────────────────────────────────────

class InstructorDeleteResponse(BaseModel):
    """Response for DELETE /api/admin/instructors/{id} — §2.14e."""

    message: str
    instructor_id: UUID
    deleted: bool


# ── Create / Update (form-data parsed as Form fields in router) ───────────────

class InstructorCreate(BaseModel):
    """Admin create — §2.14c."""

    name: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=2, max_length=150)
    bio: str | None = Field(None, max_length=2000)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    is_active: bool = True


class InstructorUpdate(BaseModel):
    """Admin update — §2.14d (all fields optional)."""

    name: str | None = Field(None, min_length=2, max_length=100)
    title: str | None = Field(None, min_length=2, max_length=150)
    bio: str | None = Field(None, max_length=2000)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    is_active: bool | None = None
