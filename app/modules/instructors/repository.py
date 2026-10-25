"""Instructor data-access layer."""

from __future__ import annotations

from math import ceil
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import Course, CourseStatus, Enrollment, Instructor


class InstructorRepository:
    """Repository for instructor database operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_options(self) -> Sequence[Instructor]:
        """Return active, non-deleted instructors for dropdowns (§2.14f)."""
        stmt = (
            select(Instructor)
            .where(Instructor.deleted_at.is_(None), Instructor.is_active.is_(True))
            .order_by(Instructor.name.asc())
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def list_admin(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        status_filter: str = "all",
        search: str | None = None,
    ) -> tuple[list[tuple[Instructor, int]], int]:
        """Return paginated instructors with courses_count and total count (§2.14a)."""
        # Base filter
        filters = [Instructor.deleted_at.is_(None)]
        if status_filter == "active":
            filters.append(Instructor.is_active.is_(True))
        elif status_filter == "suspended":
            filters.append(Instructor.is_active.is_(False))

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Instructor.name).like(term),
                    func.lower(Instructor.email).like(term),
                    func.lower(Instructor.title).like(term),
                )
            )

        # Count total
        count_stmt = select(func.count(Instructor.id)).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Query with courses_count
        stmt = (
            select(Instructor, func.count(Course.id).label("courses_count"))
            .outerjoin(
                Course,
                (Course.instructor_id == Instructor.id) & Course.deleted_at.is_(None),
            )
            .where(*filters)
            .group_by(Instructor.id)
            .order_by(Instructor.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows], total

    async def get_by_id(
        self, instructor_id: UUID, include_deleted: bool = False
    ) -> Instructor | None:
        """Fetch a single instructor by ID."""
        filters = [Instructor.id == instructor_id]
        if not include_deleted:
            filters.append(Instructor.deleted_at.is_(None))
        stmt = select(Instructor).where(*filters)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_assigned_courses(
        self, instructor_id: UUID
    ) -> list[tuple[Course, int]]:
        """Fetch courses assigned to an instructor with enrolled_count."""
        stmt = (
            select(Course, func.count(Enrollment.id).label("enrolled_count"))
            .outerjoin(Enrollment, Enrollment.course_id == Course.id)
            .where(
                Course.instructor_id == instructor_id,
                Course.deleted_at.is_(None),
            )
            .group_by(Course.id)
            .order_by(Course.created_at.desc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def count_published_courses(self, instructor_id: UUID) -> int:
        """Count active published courses assigned to this instructor."""
        stmt = select(func.count(Course.id)).where(
            Course.instructor_id == instructor_id,
            Course.status == CourseStatus.PUBLISHED,
            Course.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar() or 0

    async def count_courses(self, instructor_id: UUID) -> int:
        """Count all non-deleted courses assigned to this instructor."""
        stmt = select(func.count(Course.id)).where(
            Course.instructor_id == instructor_id,
            Course.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar() or 0

    async def create(
        self,
        *,
        name: str,
        title: str,
        bio: str | None,
        email: str | None,
        phone: str | None,
        is_active: bool,
        avatar_url: str | None,
    ) -> Instructor:
        """Insert a new instructor."""
        instructor = Instructor(
            name=name.strip(),
            title=title.strip(),
            bio=bio.strip() if bio else None,
            email=email.strip().lower() if email else None,
            phone=phone.strip() if phone else None,
            is_active=is_active,
            avatar_url=avatar_url,
        )
        self.db.add(instructor)
        await self.db.flush()
        return instructor

    async def soft_delete(self, instructor: Instructor) -> None:
        """Soft delete instructor by setting deleted_at."""
        instructor.deleted_at = func.now()
        instructor.is_active = False
        await self.db.flush()

    async def deactivate(self, instructor: Instructor) -> None:
        """Deactivate instructor by setting is_active=False."""
        instructor.is_active = False
        await self.db.flush()
