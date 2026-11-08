"""Progress schemas — Doc 08 §2.2, §3.1, §3.2."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Update Progress (§3.1) ────────────────────────────────────────────────────


class ProgressUpdateRequest(BaseModel):
    """Payload for POST /api/progress (§3.1)."""

    lesson_id: UUID
    current_position: float = Field(..., ge=0, description="Vị trí hiện tại tính bằng giây")
    total_duration: float = Field(..., ge=0, description="Tổng thời lượng video tính bằng giây")
    completed: bool = Field(False, description="Đánh dấu hoàn thành bài học")


class ProgressUpdateResponse(BaseModel):
    """Response for POST /api/progress (§3.1)."""

    message: str = "OK"
    course_progress_percent: float


# ── Progress Overview (§3.2) ──────────────────────────────────────────────────


class CourseProgressOverviewItem(BaseModel):
    """Course progress summary item in overview."""

    model_config = ConfigDict(from_attributes=True)

    course_id: UUID
    course_title: str
    thumbnail_url: str | None = None
    progress_percent: float
    completed_lessons: int
    total_lessons: int


class ProgressOverviewResponse(BaseModel):
    """Response for GET /api/progress/overview (§3.2)."""

    model_config = ConfigDict(from_attributes=True)

    total_enrolled_courses: int
    total_hours_watched: float
    total_lessons_completed: int
    courses: list[CourseProgressOverviewItem] = Field(default_factory=list)


# ── Continue Learning (§2.2) ──────────────────────────────────────────────────


class ContinueLearningItem(BaseModel):
    """Item for GET /api/progress/continue (§2.2)."""

    model_config = ConfigDict(from_attributes=True)

    course_id: UUID
    course_title: str
    course_thumbnail_url: str | None = None
    next_lesson_id: UUID
    next_lesson_title: str
    last_position: float = 0.0
    progress_percent: float = 0.0
    last_watched_at: datetime


class ContinueLearningResponse(BaseModel):
    """Response wrapper for GET /api/progress/continue (§2.2)."""

    data: list[ContinueLearningItem]
