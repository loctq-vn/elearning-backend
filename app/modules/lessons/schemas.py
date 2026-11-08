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


# ── Lesson Player Schemas (§2.7) ──────────────────────────────────────────────


class TranscriptSegmentOut(BaseModel):
    """Transcript segment for player subtitle."""

    model_config = ConfigDict(from_attributes=True)

    start: float
    end: float
    text: str


class VideoChapterOut(BaseModel):
    """Timestamp chapter marker within a video."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    start_time: float


class QuizMarkerOut(BaseModel):
    """In-video quiz marker."""

    model_config = ConfigDict(from_attributes=True)

    quiz_id: UUID
    timestamp: float
    is_answered: bool = False


class LessonPlayerOut(BaseModel):
    """Full player data for GET /api/lessons/{lesson_id} (§2.7)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    course_id: UUID
    chapter_id: UUID
    hls_stream_url: str
    duration: int = 0
    last_position: float = 0.0
    transcript: list[TranscriptSegmentOut] = Field(default_factory=list)
    chapters: list[VideoChapterOut] = Field(default_factory=list)
    quiz_markers: list[QuizMarkerOut] = Field(default_factory=list)
    next_lesson_id: UUID | None = None
    prev_lesson_id: UUID | None = None
