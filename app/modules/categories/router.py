"""Category endpoints — public §2.4 + admin CRUD."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models.schema import User, UserRole
from app.db.session import get_db_session
from app.modules.categories.schemas import (
    CategoryCreate,
    CategoryDeleteResponse,
    CategoryDetailOut,
    CategoryListResponse,
    CategoryUpdate,
)
from app.modules.categories.service import CategoryService
from app.core.errors import AppError

router = APIRouter(tags=["categories"])


def _require_admin(current_user: User) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AppError(status_code=403, code="FORBIDDEN", message="Chỉ quản trị viên mới có quyền thực hiện.")
    return current_user


# ── Public ────────────────────────────────────────────────────────────────────


@router.get(
    "/categories",
    response_model=CategoryListResponse,
    summary="Lấy danh sách danh mục (public §2.4)",
)
async def list_categories(
    db: AsyncSession = Depends(get_db_session),
) -> CategoryListResponse:
    """Trả danh sách tất cả danh mục kèm số khóa học đã xuất bản."""
    return await CategoryService(db).list_public()


# ── Admin ─────────────────────────────────────────────────────────────────────


@router.post(
    "/admin/categories",
    response_model=CategoryDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: tạo danh mục mới",
)
async def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryDetailOut:
    _require_admin(current_user)
    return await CategoryService(db).create(payload)


@router.put(
    "/admin/categories/{category_id}",
    response_model=CategoryDetailOut,
    summary="Admin: cập nhật danh mục",
)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryDetailOut:
    _require_admin(current_user)
    return await CategoryService(db).update(category_id, payload)


@router.delete(
    "/admin/categories/{category_id}",
    response_model=CategoryDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: xóa danh mục",
)
async def delete_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryDeleteResponse:
    _require_admin(current_user)
    return await CategoryService(db).delete(category_id)
