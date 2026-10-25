"""Category business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.categories.repository import CategoryRepository
from app.modules.categories.schemas import (
    CategoryCreate,
    CategoryDeleteResponse,
    CategoryDetailOut,
    CategoryListResponse,
    CategoryOut,
    CategoryUpdate,
)


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CategoryRepository(db)

    async def list_public(self) -> CategoryListResponse:
        """Return all categories with published course counts."""
        rows = await self.repo.list_with_course_count()
        return CategoryListResponse(
            data=[
                CategoryOut(id=cat.id, name=cat.name, course_count=count)
                for cat, count in rows
            ]
        )

    async def get_or_404(self, category_id: UUID) -> CategoryDetailOut:
        cat = await self.repo.get_by_id(category_id)
        if not cat:
            raise AppError(status_code=404, code="NOT_FOUND", message="Danh mục không tồn tại.")
        return CategoryDetailOut(id=cat.id, name=cat.name, slug=cat.slug, description=cat.description)

    # ── Admin operations ─────────────────────────────────────────────────────

    async def create(self, payload: CategoryCreate) -> CategoryDetailOut:
        if await self.repo.get_by_name(payload.name):
            raise AppError(status_code=409, code="CONFLICT_CATEGORY_NAME", message="Tên danh mục đã tồn tại.")
        if await self.repo.get_by_slug(payload.slug):
            raise AppError(status_code=409, code="CONFLICT_CATEGORY_SLUG", message="Slug đã được sử dụng.")
        cat = await self.repo.create(
            name=payload.name, slug=payload.slug, description=payload.description
        )
        await self.db.commit()
        return CategoryDetailOut(id=cat.id, name=cat.name, slug=cat.slug, description=cat.description)

    async def update(self, category_id: UUID, payload: CategoryUpdate) -> CategoryDetailOut:
        cat = await self.repo.get_by_id(category_id)
        if not cat:
            raise AppError(status_code=404, code="NOT_FOUND", message="Danh mục không tồn tại.")
        updates: dict[str, object] = {}
        if payload.name is not None:
            existing = await self.repo.get_by_name(payload.name)
            if existing and existing.id != category_id:
                raise AppError(status_code=409, code="CONFLICT_CATEGORY_NAME", message="Tên danh mục đã tồn tại.")
            updates["name"] = payload.name.strip()
        if payload.slug is not None:
            existing = await self.repo.get_by_slug(payload.slug)
            if existing and existing.id != category_id:
                raise AppError(status_code=409, code="CONFLICT_CATEGORY_SLUG", message="Slug đã được sử dụng.")
            updates["slug"] = payload.slug.strip().lower()
        if payload.description is not None:
            updates["description"] = payload.description
        if updates:
            cat = await self.repo.update(cat, **updates)
        await self.db.commit()
        return CategoryDetailOut(id=cat.id, name=cat.name, slug=cat.slug, description=cat.description)

    async def delete(self, category_id: UUID) -> CategoryDeleteResponse:
        cat = await self.repo.get_by_id(category_id)
        if not cat:
            raise AppError(status_code=404, code="NOT_FOUND", message="Danh mục không tồn tại.")

        course_count = await self.repo.count_courses(category_id)
        if course_count > 0:
            raise AppError(
                status_code=409,
                code="CATEGORY_HAS_COURSES",
                message="Không thể xóa danh mục đang chứa khóa học.",
            )

        await self.repo.delete(cat)
        await self.db.commit()
        return CategoryDeleteResponse(
            message="Đã xóa danh mục thành công.",
            category_id=category_id,
        )
