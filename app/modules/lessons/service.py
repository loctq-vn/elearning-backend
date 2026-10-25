"""Chapter and Lesson business logic layer."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage import S3StorageAdapter, video_raw_key
from app.core.config import settings
from app.core.errors import AppError
from app.db.models.schema import Course, VideoOverallStatus
from app.modules.lessons.repository import LessonRepository
from app.modules.lessons.schemas import (
    ChapterCreate,
    ChapterDeleteResponse,
    ChapterItem,
    ChapterUpdate,
    CourseReorderRequest,
    LessonCreateResponse,
    LessonDeleteResponse,
    LessonDetailOut,
    ReorderResponse,
)

ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "video/x-matroska",
    "application/octet-stream",  # Fallback for some browsers
}
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB


class LessonService:
    """Service handling chapters and lessons."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = LessonRepository(db)
        self.storage = S3StorageAdapter(settings)

    # ── Chapters ──────────────────────────────────────────────────────────────

    async def create_chapter(self, course_id: UUID, payload: ChapterCreate) -> ChapterItem:
        """Create a chapter within a course (§2.12a)."""
        course = (
            await self.db.execute(
                select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if not course:
            raise AppError(
                status_code=404,
                code="COURSE_NOT_FOUND",
                message="Không tìm thấy khóa học yêu cầu.",
            )

        order_idx = (
            payload.order
            if payload.order is not None
            else await self.repo.get_next_chapter_order(course_id)
        )

        chapter = await self.repo.create_chapter(
            course_id=course_id,
            title=payload.title,
            order_index=order_idx,
        )
        await self.db.commit()
        await self.db.refresh(chapter)

        return ChapterItem(
            id=chapter.id,
            title=chapter.title,
            order=chapter.order_index,
            course_id=chapter.course_id,
        )

    async def update_chapter(
        self, chapter_id: UUID, payload: ChapterUpdate
    ) -> ChapterItem:
        """Update chapter title (§2.12b)."""
        chapter = await self.repo.get_chapter(chapter_id)
        if not chapter:
            raise AppError(
                status_code=404,
                code="CHAPTER_NOT_FOUND",
                message="Không tìm thấy chương học yêu cầu.",
            )

        if payload.title is not None:
            chapter.title = payload.title.strip()

        await self.db.commit()
        await self.db.refresh(chapter)

        return ChapterItem(
            id=chapter.id,
            title=chapter.title,
            order=chapter.order_index,
            course_id=chapter.course_id,
        )

    async def delete_chapter(self, chapter_id: UUID) -> ChapterDeleteResponse:
        """Delete chapter with cascade safeguard (§2.12c)."""
        chapter = await self.repo.get_chapter(chapter_id)
        if not chapter:
            raise AppError(
                status_code=404,
                code="CHAPTER_NOT_FOUND",
                message="Không tìm thấy chương học yêu cầu.",
            )

        # Safeguard: cannot delete chapter if any lesson has processing/completed video
        has_active = await self.repo.has_active_video_in_chapter(chapter_id)
        if has_active:
            raise AppError(
                status_code=409,
                code="CHAPTER_HAS_ACTIVE_VIDEO",
                message="Không thể xóa chương học có video đang xử lý hoặc đã hoàn tất.",
            )

        await self.repo.delete_chapter(chapter)
        await self.db.commit()

        return ChapterDeleteResponse(
            message="Đã xóa chương học thành công.",
            chapter_id=chapter_id,
        )

    async def reorder_course(
        self, course_id: UUID, payload: CourseReorderRequest
    ) -> ReorderResponse:
        """Reorder chapters and lessons in a course (§2.12d)."""
        course = (
            await self.db.execute(
                select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if not course:
            raise AppError(
                status_code=404,
                code="COURSE_NOT_FOUND",
                message="Không tìm thấy khóa học yêu cầu.",
            )

        chapters_data = [
            {
                "id": c.id,
                "order": c.order,
                "lessons": [{"id": l.id, "order": l.order} for l in c.lessons],
            }
            for c in payload.chapters
        ]

        await self.repo.reorder_structure(course_id, chapters_data)
        await self.db.commit()

        return ReorderResponse(message="Sắp xếp lại thành công.")

    # ── Lessons ───────────────────────────────────────────────────────────────

    async def _handle_video_upload(
        self, video_id: UUID, video_file: UploadFile
    ) -> tuple[str, int, str]:
        """Validate and upload video file to S3."""
        content_type = video_file.content_type or "video/mp4"
        if (
            content_type not in ALLOWED_VIDEO_TYPES
            and not content_type.startswith("video/")
        ):
            raise AppError(
                status_code=400,
                code="INVALID_VIDEO_TYPE",
                message="Định dạng video không được hỗ trợ.",
            )

        content = await video_file.read()
        file_size = len(content)
        if file_size > MAX_VIDEO_SIZE:
            raise AppError(
                status_code=400,
                code="FILE_TOO_LARGE",
                message="Kích thước video không được vượt quá 500MB.",
            )

        key = video_raw_key(str(video_id), video_file.filename or "video.mp4")
        url = self.storage.upload_file(content, key, content_type)
        return url, file_size, content_type

    async def create_lesson(
        self,
        chapter_id: UUID,
        *,
        title: str,
        description: str | None,
        order: int | None,
        is_trial_allowed: bool,
        video_file: UploadFile | None,
    ) -> LessonCreateResponse:
        """Create a new lesson in a chapter (§2.13a)."""
        chapter = await self.repo.get_chapter(chapter_id)
        if not chapter:
            raise AppError(
                status_code=404,
                code="CHAPTER_NOT_FOUND",
                message="Không tìm thấy chương học yêu cầu.",
            )

        order_idx = (
            order
            if order is not None
            else await self.repo.get_next_lesson_order(chapter_id)
        )

        lesson = await self.repo.create_lesson(
            chapter_id=chapter_id,
            course_id=chapter.course_id,
            title=title,
            description=description,
            order_index=order_idx,
            is_trial_allowed=is_trial_allowed,
        )

        video_id: UUID | None = None
        pipeline_status: str | None = None

        if video_file and video_file.filename:
            video_id = uuid4()
            url, file_size, content_type = await self._handle_video_upload(
                video_id, video_file
            )
            await self.repo.create_or_update_video(
                video_id=video_id,
                lesson_id=lesson.id,
                original_filename=video_file.filename,
                file_size_bytes=file_size,
                mime_type=content_type,
                raw_storage_url=url,
                overall_status=VideoOverallStatus.UPLOADING,
            )
            pipeline_status = VideoOverallStatus.UPLOADING.value

        await self.db.commit()
        await self.db.refresh(lesson)

        return LessonCreateResponse(
            id=lesson.id,
            title=lesson.title,
            video_id=video_id,
            pipeline_status=pipeline_status,
        )

    async def update_lesson(
        self,
        lesson_id: UUID,
        *,
        title: str | None,
        description: str | None,
        order: int | None,
        is_trial_allowed: bool | None,
        video_file: UploadFile | None,
    ) -> LessonDetailOut:
        """Update existing lesson (§2.13b)."""
        lesson_with_video = await self.repo.get_lesson_with_video(lesson_id)
        if not lesson_with_video:
            raise AppError(
                status_code=404,
                code="LESSON_NOT_FOUND",
                message="Không tìm thấy bài học yêu cầu.",
            )

        lesson, existing_video = lesson_with_video

        if title is not None:
            lesson.title = title.strip()
        if description is not None:
            lesson.description = description.strip() if description else None
        if order is not None:
            lesson.order_index = order
        if is_trial_allowed is not None:
            lesson.is_trial_allowed = is_trial_allowed

        video_record = existing_video
        if video_file and video_file.filename:
            new_video_id = existing_video.id if existing_video else uuid4()
            url, file_size, content_type = await self._handle_video_upload(
                new_video_id, video_file
            )
            video_record = await self.repo.create_or_update_video(
                video_id=new_video_id,
                lesson_id=lesson.id,
                original_filename=video_file.filename,
                file_size_bytes=file_size,
                mime_type=content_type,
                raw_storage_url=url,
                overall_status=VideoOverallStatus.UPLOADING,
            )

        await self.db.commit()
        await self.db.refresh(lesson)

        v_status = (
            video_record.overall_status.value
            if video_record and hasattr(video_record.overall_status, "value")
            else (str(video_record.overall_status) if video_record else None)
        )

        return LessonDetailOut(
            id=lesson.id,
            title=lesson.title,
            description=lesson.description,
            chapter_id=lesson.chapter_id,
            course_id=lesson.course_id,
            order=lesson.order_index,
            duration_seconds=lesson.duration_seconds,
            is_trial_allowed=lesson.is_trial_allowed,
            video_id=video_record.id if video_record else None,
            video_status=v_status,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at,
        )

    async def delete_lesson(self, lesson_id: UUID) -> LessonDeleteResponse:
        """Delete lesson (§2.13c)."""
        lesson = await self.repo.get_lesson(lesson_id)
        if not lesson:
            raise AppError(
                status_code=404,
                code="LESSON_NOT_FOUND",
                message="Không tìm thấy bài học yêu cầu.",
            )

        await self.repo.delete_lesson(lesson)
        await self.db.commit()

        return LessonDeleteResponse(
            message="Đã xóa bài học thành công.",
            lesson_id=lesson_id,
        )
