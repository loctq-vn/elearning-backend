"""Chapter and Lesson schemas — Doc 08 §2.12, 2.13."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Chapter Schemas (§2.12) ───────────────────────────────────────────────────


class ChapterCreate(BaseModel):
    """Payload to create a chapter — §2.12a."""

    title: str = Field(..., min_length=2, max_length=255)
    order: int | None = Field(None, ge=0)


class ChapterUpdate(BaseModel):
    """Payload to update a chapter — §2.12b."""

    title: str | None = Field(None, min_length=2, max_length=255)


class ChapterItem(BaseModel):
    """Chapter response item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    order: int
    course_id: UUID


class ChapterDeleteResponse(BaseModel):
    """Response for chapter deletion — §2.12c."""

    message: str
    chapter_id: UUID


# ── Reorder Schemas (§2.12d) ──────────────────────────────────────────────────


class LessonReorderItem(BaseModel):
    """Single lesson reorder item."""

    id: UUID
    order: int = Field(..., ge=0)


class ChapterReorderItem(BaseModel):
    """Chapter and nested lessons reorder item."""

    id: UUID
    order: int = Field(..., ge=0)
    lessons: list[LessonReorderItem] = Field(default_factory=list)


class CourseReorderRequest(BaseModel):
    """Payload for PUT /api/admin/courses/{id}/reorder."""

    chapters: list[ChapterReorderItem]


class ReorderResponse(BaseModel):
    """Response for reorder endpoint."""

    message: str


# ── Lesson Schemas (§2.13) ────────────────────────────────────────────────────


class LessonCreateResponse(BaseModel):
    """Response for POST /api/admin/chapters/{id}/lessons — §2.13a."""

    id: UUID
    title: str
    video_id: UUID | None = None
    pipeline_status: str | None = None


class LessonDetailOut(BaseModel):
    """Lesson detail response after create/update."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    chapter_id: UUID
    course_id: UUID
    order: int
    duration_seconds: float | None = None
    is_trial_allowed: bool = False
    video_id: UUID | None = None
    video_status: str | None = None
    created_at: datetime
    updated_at: datetime


class LessonDeleteResponse(BaseModel):
    """Response for lesson deletion — §2.13c."""

    message: str
    lesson_id: UUID
