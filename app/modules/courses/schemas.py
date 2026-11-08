"""Course schemas for public portal and admin management — Doc 08 §2.1, 2.3, 2.5, 2.9, 2.10, 2.11."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Nested sub-schemas ────────────────────────────────────────────────────────


class CategorySimple(BaseModel):
    """Minimal category object inside course detail."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class InstructorProfileOut(BaseModel):
    """Instructor profile embedded in course detail."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    title: str
    bio: str | None = None
    avatar_url: str | None = None


class LessonSummaryOut(BaseModel):
    """Summary of a lesson inside a chapter."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    order: int
    duration: int = 0
    is_locked: bool = True
    is_completed: bool | None = None
    has_quiz: bool = False
    has_exercise: bool = False


class ChapterOut(BaseModel):
    """Chapter with nested lessons."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    order: int
    lessons: list[LessonSummaryOut] = Field(default_factory=list)


# ── Public Endpoints ──────────────────────────────────────────────────────────


class FeaturedCourse(BaseModel):
    """Item for GET /api/courses/featured (§2.1)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    thumbnail_url: str | None = None
    price: int
    original_price: int | None = None
    rating_avg: float | None = None
    enrolled_count: int = 0
    banner_url: str | None = None
    instructor_name: str | None = None
    instructor_avatar_url: str | None = None


class CourseListItem(BaseModel):
    """Item for paginated GET /api/courses (§2.3)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    thumbnail_url: str | None = None
    price: int
    original_price: int | None = None
    rating_avg: float | None = None
    rating_count: int | None = None
    enrolled_count: int = 0
    category_name: str | None = None
    instructor_name: str | None = None
    instructor_avatar_url: str | None = None
    status: str | None = None
    created_at: datetime


class CourseListResponse(BaseModel):
    """Paginated course list response."""

    data: list[CourseListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class CourseDetail(BaseModel):
    """Full course details — GET /api/courses/{id} (§2.5) & PUT /api/admin/courses/{id} (§2.10)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    price: int
    original_price: int | None = None
    rating_avg: float | None = None
    rating_count: int | None = None
    enrolled_count: int = 0
    category: CategorySimple | None = None
    instructor: InstructorProfileOut | None = None
    is_enrolled: bool = False
    progress_percent: float | None = None
    chapters: list[ChapterOut] = Field(default_factory=list)
    total_lessons: int = 0
    total_duration: int = 0
    status: str | None = None
    created_at: datetime
    updated_at: datetime


# ── Admin Endpoints ───────────────────────────────────────────────────────────


class CourseCreateResponse(BaseModel):
    """Response for POST /api/admin/courses (§2.9)."""

    id: UUID
    title: str
    status: str
    created_at: datetime


class CourseDeleteResponse(BaseModel):
    """Response for DELETE /api/admin/courses/{id} (§2.11)."""

    message: str
    course_id: UUID


# ── Enrollment & My Courses (§2.6, §2.8) ──────────────────────────────────────


class EnrollmentResponse(BaseModel):
    """Response for POST /api/courses/{course_id}/enroll (§2.6)."""

    model_config = ConfigDict(from_attributes=True)

    enrollment_id: UUID
    course_id: UUID
    first_lesson_id: UUID | None = None
    enrolled_at: datetime


class MyCourseItem(BaseModel):
    """Item for GET /api/my-courses (§2.8)."""

    model_config = ConfigDict(from_attributes=True)

    course_id: UUID
    title: str
    thumbnail_url: str | None = None
    progress_percent: float = 0.0
    total_lessons: int = 0
    completed_lessons: int = 0
    next_lesson_id: UUID | None = None
    next_lesson_title: str | None = None
    last_position: float = 0.0
    enrolled_at: datetime
    completed_at: datetime | None = None


class MyCourseListResponse(BaseModel):
    """Response for GET /api/my-courses (§2.8)."""

    data: list[MyCourseItem]
