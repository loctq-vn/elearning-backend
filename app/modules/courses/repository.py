"""Course data-access layer."""

from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import (
    Category,
    Chapter,
    Course,
    CourseStatus,
    Enrollment,
    Exam,
    Instructor,
    Lesson,
    LessonProgress,
    Question,
)


class CourseRepository:
    """Repository handling course database queries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_featured(self, limit: int = 10) -> list[tuple[Course, str | None, str | None, int]]:
        """Fetch published courses sorted by enrolled_count DESC (§2.1)."""
        stmt = (
            select(
                Course,
                Instructor.name.label("instructor_name"),
                Instructor.avatar_url.label("instructor_avatar_url"),
                func.count(Enrollment.id).label("enrolled_count"),
            )
            .outerjoin(Instructor, (Instructor.id == Course.instructor_id) & Instructor.deleted_at.is_(None))
            .outerjoin(Enrollment, Enrollment.course_id == Course.id)
            .where(
                Course.status == CourseStatus.PUBLISHED,
                Course.deleted_at.is_(None),
            )
            .group_by(Course.id, Instructor.name, Instructor.avatar_url)
            .order_by(func.count(Enrollment.id).desc(), Course.created_at.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return [(r[0], r[1], r[2], r[3]) for r in rows]

    async def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 12,
        search: str | None = None,
        category_id: UUID | None = None,
        instructor_id: UUID | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        sort_by: str = "newest",
        status_filter: str | None = None,
        is_admin: bool = False,
    ) -> tuple[list[tuple[Course, str | None, str | None, str | None, int]], int]:
        """Fetch filtered and paginated courses (§2.3)."""
        filters: list[Any] = [Course.deleted_at.is_(None)]

        if not is_admin:
            filters.append(Course.status == CourseStatus.PUBLISHED)
        elif status_filter and status_filter.lower() in {s.value for s in CourseStatus}:
            filters.append(Course.status == CourseStatus(status_filter.lower()))

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Course.title).like(term),
                    func.lower(Course.description).like(term),
                )
            )

        if category_id:
            filters.append(Course.category_id == category_id)

        if instructor_id:
            filters.append(Course.instructor_id == instructor_id)

        if price_min is not None:
            filters.append(Course.price >= price_min)

        if price_max is not None:
            filters.append(Course.price <= price_max)

        # Count total matches
        count_stmt = select(func.count(Course.id)).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Enrolled count label
        enrolled_col = func.count(Enrollment.id).label("enrolled_count")

        query = (
            select(
                Course,
                Category.name.label("category_name"),
                Instructor.name.label("instructor_name"),
                Instructor.avatar_url.label("instructor_avatar_url"),
                enrolled_col,
            )
            .outerjoin(Category, Category.id == Course.category_id)
            .outerjoin(Instructor, (Instructor.id == Course.instructor_id) & Instructor.deleted_at.is_(None))
            .outerjoin(Enrollment, Enrollment.course_id == Course.id)
            .where(*filters)
            .group_by(Course.id, Category.name, Instructor.name, Instructor.avatar_url)
        )

        # Apply sorting
        if sort_by == "recommended":
            query = query.order_by(enrolled_col.desc(), Course.created_at.desc())
        elif sort_by == "price_asc":
            query = query.order_by(Course.price.asc(), Course.created_at.desc())
        elif sort_by == "price_desc":
            query = query.order_by(Course.price.desc(), Course.created_at.desc())
        else:  # newest
            query = query.order_by(Course.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(query)).all()
        return [(r[0], r[1], r[2], r[3], r[4]) for r in rows], total

    async def get_by_id(self, course_id: UUID, include_deleted: bool = False) -> Course | None:
        """Fetch raw course record."""
        filters = [Course.id == course_id]
        if not include_deleted:
            filters.append(Course.deleted_at.is_(None))
        stmt = select(Course).where(*filters)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_detail_with_relations(
        self, course_id: UUID
    ) -> tuple[Course, Category | None, Instructor | None, int] | None:
        """Fetch course with category, instructor, and total enrollments."""
        stmt = (
            select(
                Course,
                Category,
                Instructor,
                func.count(Enrollment.id).label("enrolled_count"),
            )
            .outerjoin(Category, Category.id == Course.category_id)
            .outerjoin(Instructor, (Instructor.id == Course.instructor_id) & Instructor.deleted_at.is_(None))
            .outerjoin(Enrollment, Enrollment.course_id == Course.id)
            .where(Course.id == course_id, Course.deleted_at.is_(None))
            .group_by(Course.id, Category.id, Instructor.id)
        )
        row = (await self.db.execute(stmt)).first()
        if not row:
            return None
        return row[0], row[1], row[2], row[3]

    async def get_enrollment(self, user_id: UUID, course_id: UUID) -> Enrollment | None:
        """Fetch enrollment record for a specific user and course."""
        stmt = select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def count_enrollments(self, course_id: UUID) -> int:
        """Count total enrollments for a course."""
        stmt = select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
        return (await self.db.execute(stmt)).scalar() or 0

    async def get_course_structure(
        self, course_id: UUID, user_id: UUID | None = None
    ) -> list[tuple[Chapter, list[tuple[Lesson, bool, bool, bool]]]]:
        """
        Fetch all chapters and lessons for a course in order.
        Each lesson returns: (Lesson, is_completed, has_quiz, has_exercise).
        """
        # Fetch chapters
        chap_stmt = (
            select(Chapter)
            .where(Chapter.course_id == course_id)
            .order_by(Chapter.order_index.asc())
        )
        chapters = (await self.db.execute(chap_stmt)).scalars().all()
        if not chapters:
            return []

        chapter_ids = [c.id for c in chapters]

        # Fetch lessons
        less_stmt = (
            select(Lesson)
            .where(Lesson.chapter_id.in_(chapter_ids))
            .order_by(Lesson.order_index.asc())
        )
        lessons = (await self.db.execute(less_stmt)).scalars().all()
        lesson_ids = [l.id for l in lessons]

        # Progress map
        completed_lessons: set[UUID] = set()
        if user_id and lesson_ids:
            prog_stmt = select(LessonProgress.lesson_id).where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id.in_(lesson_ids),
                LessonProgress.is_completed.is_(True),
            )
            completed_lessons = set((await self.db.execute(prog_stmt)).scalars().all())

        # Exam / Quiz map
        quiz_lessons: set[UUID] = set()
        exercise_lessons: set[UUID] = set()
        if lesson_ids:
            exam_stmt = select(Exam.lesson_id, Exam.exam_type).where(
                Exam.lesson_id.in_(lesson_ids)
            )
            exam_rows = (await self.db.execute(exam_stmt)).all()
            for l_id, e_type in exam_rows:
                if l_id:
                    e_val = e_type.value if hasattr(e_type, "value") else str(e_type)
                    if "quiz" in e_val.lower():
                        quiz_lessons.add(l_id)
                    else:
                        exercise_lessons.add(l_id)

            # Check Question table directly as well
            q_stmt = select(Question.lesson_id).where(Question.lesson_id.in_(lesson_ids))
            q_rows = (await self.db.execute(q_stmt)).scalars().all()
            for l_id in q_rows:
                if l_id:
                    quiz_lessons.add(l_id)

        # Group lessons by chapter
        grouped: dict[UUID, list[tuple[Lesson, bool, bool, bool]]] = {c.id: [] for c in chapters}
        for l in lessons:
            is_comp = l.id in completed_lessons
            has_q = l.id in quiz_lessons
            has_ex = l.id in exercise_lessons
            if l.chapter_id in grouped:
                grouped[l.chapter_id].append((l, is_comp, has_q, has_ex))

        return [(c, grouped[c.id]) for c in chapters]

    async def count_chapters_and_lessons(self, course_id: UUID) -> tuple[int, int]:
        """Count chapters and lessons for publish readiness validation."""
        c_count = (
            await self.db.execute(
                select(func.count(Chapter.id)).where(Chapter.course_id == course_id)
            )
        ).scalar() or 0

        l_count = (
            await self.db.execute(
                select(func.count(Lesson.id)).where(Lesson.course_id == course_id)
            )
        ).scalar() or 0

        return c_count, l_count

    async def create(
        self,
        *,
        title: str,
        description: str | None,
        category_id: UUID,
        instructor_id: UUID | None,
        price: int,
        status: CourseStatus,
        thumbnail_url: str | None,
        created_by: UUID | None,
    ) -> Course:
        """Insert a new course record."""
        course = Course(
            title=title.strip(),
            description=description.strip() if description else None,
            category_id=category_id,
            instructor_id=instructor_id,
            price=price,
            status=status,
            thumbnail_url=thumbnail_url,
            created_by=created_by,
        )
        self.db.add(course)
        await self.db.flush()
        return course

    async def soft_delete(self, course: Course) -> None:
        """Soft delete course."""
        course.deleted_at = func.now()
        await self.db.flush()
