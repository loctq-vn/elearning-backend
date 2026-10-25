"""Category data-access layer."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import Category, Course, CourseStatus


class CategoryRepository:
    """Repository for category CRUD and aggregations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Queries ──────────────────────────────────────────────────────────────

    async def list_with_course_count(self) -> list[tuple[Category, int]]:
        """Return all categories with count of published courses."""
        stmt = (
            select(Category, func.count(Course.id).label("course_count"))
            .outerjoin(
                Course,
                (Course.category_id == Category.id)
                & (Course.status == CourseStatus.PUBLISHED)
                & Course.deleted_at.is_(None),
            )
            .group_by(Category.id)
            .order_by(Category.name)
        )
        rows = (await self.db.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def get_by_id(self, category_id: UUID) -> Category | None:
        result = await self.db.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Category | None:
        result = await self.db.execute(
            select(Category).where(Category.slug == slug.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Category | None:
        result = await self.db.execute(
            select(Category).where(func.lower(Category.name) == name.strip().lower())
        )
        return result.scalar_one_or_none()

    async def count_courses(self, category_id: UUID) -> int:
        """Count active courses belonging to this category."""
        stmt = select(func.count(Course.id)).where(
            Course.category_id == category_id,
            Course.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar() or 0

    # ── Mutations ─────────────────────────────────────────────────────────────

    async def create(self, *, name: str, slug: str, description: str | None) -> Category:
        category = Category(name=name.strip(), slug=slug.strip().lower(), description=description)
        self.db.add(category)
        await self.db.flush()
        return category

    async def update(self, category: Category, **kwargs: object) -> Category:
        for key, value in kwargs.items():
            setattr(category, key, value)
        await self.db.flush()
        return category

    async def delete(self, category: Category) -> None:
        await self.db.delete(category)
        await self.db.flush()
