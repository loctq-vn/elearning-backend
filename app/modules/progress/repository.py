"""Progress data-access layer."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import Chapter, Course, Enrollment, Lesson, LessonProgress


class ProgressRepository:
    """Repository handling watch progress, course progress calculation, and overview queries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_lesson(self, lesson_id: UUID) -> Lesson | None:
        """Fetch lesson by ID."""
        stmt = select(Lesson).where(Lesson.id == lesson_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def is_user_enrolled_or_trial(self, user_id: UUID, lesson: Lesson) -> bool:
        """Check if user has permission to access and track progress on this lesson."""
        if lesson.is_trial_allowed:
            return True
        stmt = select(Enrollment.id).where(
            Enrollment.user_id == user_id,
            Enrollment.course_id == lesson.course_id,
        )
        return (await self.db.execute(stmt)).scalar() is not None

    async def upsert_lesson_progress(
        self,
        *,
        user_id: UUID,
        lesson_id: UUID,
        current_position: float,
        is_completed: bool,
    ) -> None:
        """
        High-throughput upsert for auto-saving video watch position (§3.1).
        Preserves is_completed=True if already achieved.
        """
        now = datetime.now(timezone.utc)
        completed_at_val = now if is_completed else None

        stmt = (
            insert(LessonProgress)
            .values(
                user_id=user_id,
                lesson_id=lesson_id,
                watch_position_seconds=current_position,
                is_completed=is_completed,
                completed_at=completed_at_val,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "lesson_id"],
                set_={
                    "watch_position_seconds": current_position,
                    "is_completed": LessonProgress.is_completed | is_completed,
                    "completed_at": func.coalesce(LessonProgress.completed_at, completed_at_val),
                    "updated_at": now,
                },
            )
        )
        await self.db.execute(stmt)

    async def calculate_and_update_course_progress(
        self, *, user_id: UUID, course_id: UUID, last_lesson_id: UUID
    ) -> float:
        """Calculate course completion percentage and update the enrollment record."""
        total_stmt = select(func.count(Lesson.id)).where(Lesson.course_id == course_id)
        total_lessons = (await self.db.execute(total_stmt)).scalar() or 0

        completed_stmt = (
            select(func.count(LessonProgress.id))
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(
                Lesson.course_id == course_id,
                LessonProgress.user_id == user_id,
                LessonProgress.is_completed.is_(True),
            )
        )
        completed_lessons = (await self.db.execute(completed_stmt)).scalar() or 0

        percent = round((completed_lessons / total_lessons) * 100.0, 1) if total_lessons > 0 else 0.0

        # Update enrollment if it exists
        upd_stmt = (
            update(Enrollment)
            .where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .values(
                progress_percent=percent,
                last_lesson_id=last_lesson_id,
            )
        )
        await self.db.execute(upd_stmt)
        return percent

    async def get_overview_stats(self, user_id: UUID) -> tuple[int, float, int]:
        """Fetch overall learning statistics for user (§3.2)."""
        enrolled_stmt = select(func.count(Enrollment.id)).where(Enrollment.user_id == user_id)
        total_enrolled = (await self.db.execute(enrolled_stmt)).scalar() or 0

        seconds_stmt = select(
            func.coalesce(func.sum(LessonProgress.watch_position_seconds), 0.0)
        ).where(LessonProgress.user_id == user_id)
        total_seconds = (await self.db.execute(seconds_stmt)).scalar() or 0.0
        total_hours = round(float(total_seconds) / 3600.0, 1)

        completed_stmt = select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == user_id,
            LessonProgress.is_completed.is_(True),
        )
        total_completed = (await self.db.execute(completed_stmt)).scalar() or 0

        return total_enrolled, total_hours, total_completed

    async def list_enrolled_courses_with_progress(
        self, user_id: UUID
    ) -> list[tuple[Enrollment, Course, int, int]]:
        """
        List all enrolled courses with total and completed lessons count.
        Returns: [(Enrollment, Course, completed_lessons_count, total_lessons_count), ...]
        """
        stmt = (
            select(Enrollment, Course)
            .join(Course, Course.id == Enrollment.course_id)
            .where(
                Enrollment.user_id == user_id,
                Course.deleted_at.is_(None),
            )
            .order_by(Enrollment.enrolled_at.desc())
        )
        rows = (await self.db.execute(stmt)).all()
        results: list[tuple[Enrollment, Course, int, int]] = []

        for enrollment, course in rows:
            tot_stmt = select(func.count(Lesson.id)).where(Lesson.course_id == course.id)
            tot = (await self.db.execute(tot_stmt)).scalar() or 0

            comp_stmt = (
                select(func.count(LessonProgress.id))
                .join(Lesson, Lesson.id == LessonProgress.lesson_id)
                .where(
                    Lesson.course_id == course.id,
                    LessonProgress.user_id == user_id,
                    LessonProgress.is_completed.is_(True),
                )
            )
            comp = (await self.db.execute(comp_stmt)).scalar() or 0
            results.append((enrollment, course, comp, tot))

        return results

    async def get_ordered_course_lessons(self, course_id: UUID) -> list[Lesson]:
        """Fetch all lessons in a course ordered by chapter and lesson index."""
        stmt = (
            select(Lesson)
            .join(Chapter, Chapter.id == Lesson.chapter_id)
            .where(Lesson.course_id == course_id)
            .order_by(Chapter.order_index.asc(), Lesson.order_index.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_user_course_progress_records(
        self, user_id: UUID, course_id: UUID
    ) -> dict[UUID, LessonProgress]:
        """Fetch a map of lesson_id -> LessonProgress for a course."""
        stmt = (
            select(LessonProgress)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(
                Lesson.course_id == course_id,
                LessonProgress.user_id == user_id,
            )
        )
        records = (await self.db.execute(stmt)).scalars().all()
        return {r.lesson_id: r for r in records}
