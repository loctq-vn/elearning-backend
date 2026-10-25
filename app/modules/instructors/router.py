"""Instructor endpoints — public dropdown + admin management (§2.14)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import get_current_user
from app.db.models.schema import User, UserRole
from app.db.session import get_db_session
from app.modules.instructors.schemas import (
    AdminInstructorDetail,
    AdminInstructorListResponse,
    InstructorCreate,
    InstructorDeleteResponse,
    InstructorOption,
    InstructorUpdate,
)
from app.modules.instructors.service import InstructorService

router = APIRouter(tags=["instructors"])


def _require_admin(current_user: User) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Chỉ quản trị viên mới có quyền thực hiện.",
        )
    return current_user


# ── Public ────────────────────────────────────────────────────────────────────


@router.get(
    "/instructors/options",
    response_model=list[InstructorOption],
    summary="Lấy danh sách giảng viên rút gọn cho dropdown (public §2.14f)",
)
async def list_instructor_options(
    db: AsyncSession = Depends(get_db_session),
) -> list[InstructorOption]:
    """Trả danh sách giảng viên active để gán vào khóa học."""
    return await InstructorService(db).list_options()


# ── Admin ─────────────────────────────────────────────────────────────────────


@router.get(
    "/admin/instructors",
    response_model=AdminInstructorListResponse,
    summary="Admin: danh sách giảng viên phân trang (§2.14a)",
)
async def list_admin_instructors(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng trên trang"),
    status: str = Query("all", pattern="^(all|active|suspended)$", description="Lọc trạng thái"),
    search: str | None = Query(None, description="Tìm theo tên/email/chức danh"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AdminInstructorListResponse:
    _require_admin(current_user)
    return await InstructorService(db).list_admin(
        page=page,
        page_size=page_size,
        status_filter=status,
        search=search,
    )


@router.get(
    "/admin/instructors/{instructor_id}",
    response_model=AdminInstructorDetail,
    summary="Admin: chi tiết giảng viên (§2.14b)",
)
async def get_admin_instructor(
    instructor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AdminInstructorDetail:
    _require_admin(current_user)
    return await InstructorService(db).get_detail(instructor_id)


@router.post(
    "/admin/instructors",
    response_model=AdminInstructorDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: tạo giảng viên mới (§2.14c)",
)
async def create_instructor(
    name: str = Form(..., min_length=2, max_length=100),
    title: str = Form(..., min_length=2, max_length=150),
    bio: str | None = Form(None, max_length=2000),
    email: EmailStr | None = Form(None),
    phone: str | None = Form(None, max_length=20),
    is_active: bool = Form(True),
    avatar: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AdminInstructorDetail:
    _require_admin(current_user)
    payload = InstructorCreate(
        name=name,
        title=title,
        bio=bio,
        email=email,
        phone=phone,
        is_active=is_active,
    )
    return await InstructorService(db).create(payload, avatar)


@router.put(
    "/admin/instructors/{instructor_id}",
    response_model=AdminInstructorDetail,
    summary="Admin: cập nhật giảng viên (§2.14d)",
)
async def update_instructor(
    instructor_id: UUID,
    name: str | None = Form(None, min_length=2, max_length=100),
    title: str | None = Form(None, min_length=2, max_length=150),
    bio: str | None = Form(None, max_length=2000),
    email: EmailStr | None = Form(None),
    phone: str | None = Form(None, max_length=20),
    is_active: bool | None = Form(None),
    avatar: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AdminInstructorDetail:
    _require_admin(current_user)
    payload = InstructorUpdate(
        name=name,
        title=title,
        bio=bio,
        email=email,
        phone=phone,
        is_active=is_active,
    )
    return await InstructorService(db).update(instructor_id, payload, avatar)


@router.delete(
    "/admin/instructors/{instructor_id}",
    response_model=InstructorDeleteResponse,
    summary="Admin: xóa hoặc tạm ngưng giảng viên (§2.14e)",
)
async def delete_instructor(
    instructor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> InstructorDeleteResponse:
    _require_admin(current_user)
    return await InstructorService(db).delete(instructor_id)
