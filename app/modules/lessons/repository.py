"""Chapter and Lesson data-access layer."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import Chapter, Course, Lesson, Video, VideoOverallStatus


class LessonRepository:
    """Repository handling chapter, lesson, and video DB operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Chapter Operations ────────────────────────────────────────────────────

    async def get_chapter(self, chapter_id: UUID) -> Chapter | None:
        """Fetch chapter by ID."""
        stmt = select(Chapter).where(Chapter.id == chapter_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_next_chapter_order(self, course_id: UUID) -> int:
        """Calculate next available order_index for chapters in a course."""
        stmt = select(func.coalesce(func.max(Chapter.order_index), -1) + 1).where(
            Chapter.course_id == course_id
        )
        return (await self.db.execute(stmt)).scalar() or 0

    async def create_chapter(
        self, *, course_id: UUID, title: str, order_index: int
    ) -> Chapter:
        """Insert a new chapter."""
        chapter = Chapter(
            course_id=course_id,
            title=title.strip(),
            order_index=order_index,
        )
        self.db.add(chapter)
        await self.db.flush()
        return chapter

    async def has_active_video_in_chapter(self, chapter_id: UUID) -> bool:
        """Check if any lesson in chapter has processing or completed video."""
        active_statuses = [VideoOverallStatus.PROCESSING, VideoOverallStatus.COMPLETED]
        stmt = (
            select(Video.id)
            .join(Lesson, Lesson.id == Video.lesson_id)
            .where(
                Lesson.chapter_id == chapter_id,
                Video.overall_status.in_(active_statuses),
            )
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar() is not None

    async def delete_chapter(self, chapter: Chapter) -> None:
        """Delete chapter record."""
        await self.db.delete(chapter)
        await self.db.flush()

    # ── Reorder Operations ────────────────────────────────────────────────────

    async def reorder_structure(
        self,
        course_id: UUID,
        chapters: list[dict[str, Any]],
    ) -> None:
        """
        Reorder chapters and lessons safely avoiding unique constraint collisions.
        Uses temporary negative order indices first, then applies final order.
        """
        lesson_counter = 0
        for idx, chap in enumerate(chapters):
            temp_order = -(idx + 1000)
            await self.db.execute(
                update(Chapter)
                .where(Chapter.id == chap["id"], Chapter.course_id == course_id)
                .values(order_index=temp_order)
            )
            for less in chap.get("lessons", []):
                lesson_counter += 1
                temp_less_order = -(lesson_counter + 10000)
                await self.db.execute(
                    update(Lesson)
                    .where(Lesson.id == less["id"])
                    .values(order_index=temp_less_order)
                )

        await self.db.flush()

        # Pass 2: Set target order indices and chapter assignment
        for chap in chapters:
            await self.db.execute(
                update(Chapter)
                .where(Chapter.id == chap["id"], Chapter.course_id == course_id)
                .values(order_index=chap["order"])
            )
            for less in chap.get("lessons", []):
                await self.db.execute(
                    update(Lesson)
                    .where(Lesson.id == less["id"])
                    .values(
                        order_index=less["order"],
                        chapter_id=chap["id"],
                    )
                )

        await self.db.flush()

    # ── Lesson Operations ─────────────────────────────────────────────────────

    async def get_lesson(self, lesson_id: UUID) -> Lesson | None:
        """Fetch lesson by ID."""
        stmt = select(Lesson).where(Lesson.id == lesson_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_lesson_with_video(
        self, lesson_id: UUID
    ) -> tuple[Lesson, Video | None] | None:
        """Fetch lesson alongside attached video if present."""
        stmt = (
            select(Lesson, Video)
            .outerjoin(Video, Video.lesson_id == Lesson.id)
            .where(Lesson.id == lesson_id)
        )
        row = (await self.db.execute(stmt)).first()
        if not row:
            return None
        return row[0], row[1]

    async def get_next_lesson_order(self, chapter_id: UUID) -> int:
        """Calculate next available order_index for lessons in a chapter."""
        stmt = select(func.coalesce(func.max(Lesson.order_index), -1) + 1).where(
            Lesson.chapter_id == chapter_id
        )
        return (await self.db.execute(stmt)).scalar() or 0

    async def create_lesson(
        self,
        *,
        chapter_id: UUID,
        course_id: UUID,
        title: str,
        description: str | None,
        order_index: int,
        is_trial_allowed: bool,
    ) -> Lesson:
        """Insert a new lesson."""
        lesson = Lesson(
            chapter_id=chapter_id,
            course_id=course_id,
            title=title.strip(),
            description=description.strip() if description else None,
            order_index=order_index,
            is_trial_allowed=is_trial_allowed,
        )
        self.db.add(lesson)
        await self.db.flush()
        return lesson

    async def create_or_update_video(
        self,
        *,
        video_id: UUID,
        lesson_id: UUID,
        original_filename: str,
        file_size_bytes: int,
        mime_type: str,
        raw_storage_url: str | None,
        overall_status: VideoOverallStatus = VideoOverallStatus.UPLOADING,
    ) -> Video:
        """Create or update video record for a lesson."""
        stmt = select(Video).where(Video.lesson_id == lesson_id)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.original_filename = original_filename
            existing.file_size_bytes = file_size_bytes
            existing.mime_type = mime_type
            existing.raw_storage_url = raw_storage_url
            existing.overall_status = overall_status
            await self.db.flush()
            return existing

        video = Video(
            id=video_id,
            lesson_id=lesson_id,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            raw_storage_url=raw_storage_url,
            overall_status=overall_status,
        )
        self.db.add(video)
        await self.db.flush()
        return video

    async def delete_lesson(self, lesson: Lesson) -> None:
        """Delete lesson record."""
        await self.db.delete(lesson)
        await self.db.flush()
