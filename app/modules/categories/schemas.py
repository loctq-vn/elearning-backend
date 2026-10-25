"""Category schemas (request/response) for B3.01 §2.4."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryOut(BaseModel):
    """Single category item — used in GET /api/categories."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    course_count: int = 0


class CategoryListResponse(BaseModel):
    """Response for GET /api/categories."""

    data: list[CategoryOut]


# ── Admin schemas ────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    """Admin: create a new category."""

    name: str = Field(..., min_length=2, max_length=150, description="Tên danh mục")
    slug: str = Field(..., min_length=2, max_length=150, description="Slug đường dẫn (unique)")
    description: str | None = Field(None, max_length=1000)


class CategoryUpdate(BaseModel):
    """Admin: update an existing category (all fields optional)."""

    name: str | None = Field(None, min_length=2, max_length=150)
    slug: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = None


class CategoryDetailOut(BaseModel):
    """Full category detail including slug — used by admin."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None = None
    course_count: int = 0


class CategoryDeleteResponse(BaseModel):
    """Response for category deletion."""

    message: str
    category_id: UUID
