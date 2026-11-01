"""Progress business logic layer."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.progress.repository import ProgressRepository
from app.modules.progress.schemas import (
    ContinueLearningItem,
    ContinueLearningResponse,
    CourseProgressOverviewItem,
    ProgressOverviewResponse,
    ProgressUpdateRequest,
    ProgressUpdateResponse,
)


class ProgressService:
    """Service handling watch progress auto-save, learning overview, and continue learning."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProgressRepository(db)

    async def save_progress(
        self, user_id: UUID, payload: ProgressUpdateRequest
    ) -> ProgressUpdateResponse:
        """
        Record video watch progress every ~10s (§3.1).
        Marks completed when position reaches >= 90% of duration.
        """
        lesson = await self.repo.get_lesson(payload.lesson_id)
        if not lesson:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message="Bài học không tồn tại.",
            )

        # Access check
        has_access = await self.repo.is_user_enrolled_or_trial(user_id, lesson)
        if not has_access:
            raise AppError(
                status_code=403,
                code="NOT_ENROLLED",
                message="Vui lòng mua khóa học để ghi nhận tiến độ.",
            )

        # Completion rule: manual flag OR watched >= 90%
        auto_completed = (
            payload.total_duration > 0
            and payload.current_position >= (payload.total_duration * 0.9)
        )
        is_completed = payload.completed or auto_completed

        # Upsert position
        await self.repo.upsert_lesson_progress(
            user_id=user_id,
            lesson_id=payload.lesson_id,
            current_position=payload.current_position,
            is_completed=is_completed,
        )

        # Recalculate course percentage
        percent = await self.repo.calculate_and_update_course_progress(
            user_id=user_id,
            course_id=lesson.course_id,
            last_lesson_id=lesson.id,
        )
        await self.db.commit()

        return ProgressUpdateResponse(
            message="OK",
            course_progress_percent=percent,
        )

    async def get_overview(self, user_id: UUID) -> ProgressOverviewResponse:
        """Fetch student overview statistics and course progress cards (§3.2)."""
        total_enrolled, total_hours, total_completed = await self.repo.get_overview_stats(user_id)
        enrolled_courses = await self.repo.list_enrolled_courses_with_progress(user_id)

        course_items = [
            CourseProgressOverviewItem(
                course_id=course.id,
                course_title=course.title,
                thumbnail_url=course.thumbnail_url,
                progress_percent=enrollment.progress_percent,
                completed_lessons=completed_count,
                total_lessons=total_count,
            )
            for enrollment, course, completed_count, total_count in enrolled_courses
        ]

        return ProgressOverviewResponse(
            total_enrolled_courses=total_enrolled,
            total_hours_watched=total_hours,
            total_lessons_completed=total_completed,
            courses=course_items,
        )

    async def get_continue_learning(self, user_id: UUID) -> ContinueLearningResponse:
        """
        Fetch courses currently in progress for the student, sorted by last_watched_at DESC (§2.2).
        """
        enrolled_courses = await self.repo.list_enrolled_courses_with_progress(user_id)
        items: list[ContinueLearningItem] = []

        for enrollment, course, _completed_count, _total_count in enrolled_courses:
            # If already 100% completed, don't show in continue learning
            if enrollment.progress_percent >= 100.0:
                continue

            lessons = await self.repo.get_ordered_course_lessons(course.id)
            if not lessons:
                continue

            progress_map = await self.repo.get_user_course_progress_records(user_id, course.id)

            # Determine next lesson to watch
            next_lesson = None
            if enrollment.last_lesson_id:
                last_p = progress_map.get(enrollment.last_lesson_id)
                if last_p and not last_p.is_completed:
                    for l in lessons:
                        if l.id == enrollment.last_lesson_id:
                            next_lesson = l
                            break

            if not next_lesson:
                for l in lessons:
                    p = progress_map.get(l.id)
                    if not p or not p.is_completed:
                        next_lesson = l
                        break

            if not next_lesson:
                continue

            p_record = progress_map.get(next_lesson.id)
            last_pos = p_record.watch_position_seconds if p_record else 0.0

            # Determine last_watched_at from the most recent progress update, or enrollment date
            latest_time = enrollment.enrolled_at
            for p in progress_map.values():
                if p.updated_at and p.updated_at > latest_time:
                    latest_time = p.updated_at

            items.append(
                ContinueLearningItem(
                    course_id=course.id,
                    course_title=course.title,
                    course_thumbnail_url=course.thumbnail_url,
                    next_lesson_id=next_lesson.id,
                    next_lesson_title=next_lesson.title,
                    last_position=last_pos,
                    progress_percent=enrollment.progress_percent,
                    last_watched_at=latest_time,
                )
            )

        # Sort by last_watched_at descending
        items.sort(key=lambda item: item.last_watched_at, reverse=True)
        return ContinueLearningResponse(data=items)
