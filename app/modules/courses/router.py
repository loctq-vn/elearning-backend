"""Course endpoints — public catalog and admin management (§2.1, 2.3, 2.5, 2.9, 2.10, 2.11)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import get_current_user, get_optional_current_user
from app.db.models.schema import User, UserRole
from app.db.session import get_db_session
from app.modules.courses.schemas import (
    CourseCreateResponse,
    CourseDeleteResponse,
    CourseDetail,
    CourseListResponse,
    FeaturedCourse,
)
from app.modules.courses.service import CourseService

router = APIRouter(tags=["courses"])


def _require_admin(current_user: User) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Chỉ quản trị viên mới có quyền thực hiện.",
        )
    return current_user


# ── Public Endpoints ──────────────────────────────────────────────────────────


@router.get(
    "/courses/featured",
    response_model=list[FeaturedCourse],
    summary="Lấy danh sách khóa học nổi bật (public §2.1)",
)
async def get_featured_courses(
    limit: int = Query(10, ge=1, le=50, description="Số lượng khóa học"),
    db: AsyncSession = Depends(get_db_session),
) -> list[FeaturedCourse]:
    """Trả danh sách các khóa học đã xuất bản có lượt đăng ký cao nhất."""
    return await CourseService(db).list_featured(limit=limit)


@router.get(
    "/courses",
    response_model=CourseListResponse,
    summary="Lấy danh sách khóa học phân trang và tìm kiếm (public / admin §2.3)",
)
async def list_courses(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(12, ge=1, le=100, description="Số lượng mỗi trang"),
    search: str | None = Query(None, description="Tìm theo tên hoặc mô tả"),
    category_id: UUID | None = Query(None, description="Lọc theo danh mục"),
    instructor_id: UUID | None = Query(None, description="Lọc theo giảng viên"),
    price_min: int | None = Query(None, ge=0, description="Giá thấp nhất"),
    price_max: int | None = Query(None, ge=0, description="Giá cao nhất"),
    sort_by: str = Query("newest", pattern="^(newest|recommended|price_asc|price_desc)$", description="Tiêu chí sắp xếp"),
    status: str | None = Query(None, description="Lọc theo trạng thái (chỉ dành cho admin)"),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CourseListResponse:
    """Tìm kiếm, lọc danh mục, giảng viên và khoảng giá của các khóa học."""
    return await CourseService(db).list_paginated(
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        instructor_id=instructor_id,
        price_min=price_min,
        price_max=price_max,
        sort_by=sort_by,
        status_filter=status,
        current_user=current_user,
    )


@router.get(
    "/courses/{course_id}",
    response_model=CourseDetail,
    summary="Lấy chi tiết khóa học kèm danh sách chương bài học (public §2.5)",
)
async def get_course_detail(
    course_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CourseDetail:
    """Trả thông tin chi tiết khóa học, giảng viên, cấu trúc chương/bài và trạng thái khóa bài học."""
    return await CourseService(db).get_detail(course_id, current_user=current_user)


# ── Admin Endpoints ───────────────────────────────────────────────────────────


@router.post(
    "/admin/courses",
    response_model=CourseCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: tạo khóa học mới (§2.9)",
)
async def create_course(
    title: str = Form(..., min_length=5, max_length=200, description="Tên khóa học"),
    description: str | None = Form(None, max_length=10000, description="Mô tả chi tiết"),
    category_id: UUID = Form(..., description="ID danh mục"),
    instructor_id: UUID | None = Form(None, description="ID giảng viên phụ trách"),
    price: int = Form(0, ge=0, description="Học phí (VND)"),
    status: str = Form("draft", pattern="^(draft|published|hidden)$", description="Trạng thái xuất bản"),
    thumbnail: UploadFile | None = File(None, description="Ảnh đại diện (max 5MB)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CourseCreateResponse:
    _require_admin(current_user)
    return await CourseService(db).create(
        title=title,
        description=description,
        category_id=category_id,
        instructor_id=instructor_id,
        price=price,
        status=status,
        thumbnail=thumbnail,
        created_by=current_user.id,
    )


@router.put(
    "/admin/courses/{course_id}",
    response_model=CourseDetail,
    summary="Admin: cập nhật khóa học (§2.10)",
)
async def update_course(
    course_id: UUID,
    title: str | None = Form(None, min_length=5, max_length=200),
    description: str | None = Form(None, max_length=10000),
    category_id: UUID | None = Form(None),
    instructor_id: UUID | None = Form(None),
    price: int | None = Form(None, ge=0),
    status: str | None = Form(None, pattern="^(draft|published|hidden)$"),
    thumbnail: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CourseDetail:
    _require_admin(current_user)
    return await CourseService(db).update(
        course_id=course_id,
        title=title,
        description=description,
        category_id=category_id,
        instructor_id=instructor_id,
        price=price,
        status=status,
        thumbnail=thumbnail,
        current_user=current_user,
    )


@router.delete(
    "/admin/courses/{course_id}",
    response_model=CourseDeleteResponse,
    summary="Admin: xóa khóa học (§2.11)",
)
async def delete_course(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CourseDeleteResponse:
    _require_admin(current_user)
    return await CourseService(db).delete(course_id)
