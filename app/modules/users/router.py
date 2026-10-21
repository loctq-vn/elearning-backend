"""Users and Admin User management endpoints."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_admin
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.security import get_current_active_user
from app.db.models.schema import User
from app.db.session import get_db_session
from app.modules.users.schemas import (
    AdminUserItem,
    ChangePasswordRequest,
    LockUserResponse,
    UserProfileResponse,
)
from app.modules.users.service import UsersService

router = APIRouter(tags=["users"])


# ==========================================
# Student / Profile APIs
# ==========================================


@router.get(
    "/users/me",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[UserProfileResponse],
    summary="Xem hồ sơ cá nhân",
)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[UserProfileResponse]:
    """Lấy thông tin tài khoản của người dùng hiện tại đang đăng nhập."""
    service = UsersService(db)
    profile = await service.get_me(current_user)
    return ApiResponse(data=profile)


@router.put(
    "/users/me",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[UserProfileResponse],
    summary="Cập nhật thông tin cá nhân",
)
async def update_my_profile(
    full_name: str | None = Form(None, description="Họ và tên mới (2-100 ký tự)"),
    avatar: UploadFile | None = File(None, description="Ảnh đại diện (JPEG, PNG, WebP <= 2MB)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[UserProfileResponse]:
    """Cập nhật họ tên và/hoặc tải lên ảnh đại diện cá nhân lưu trữ S3."""
    service = UsersService(db)
    profile = await service.update_profile(current_user, full_name=full_name, avatar=avatar)
    return ApiResponse(data=profile, message="Cập nhật thông tin thành công.")


@router.put(
    "/users/me/password",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[dict[str, str]],
    summary="Đổi mật khẩu trong ứng dụng",
)
async def change_my_password(
    payload: ChangePasswordRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[dict[str, str]]:
    """Đổi mật khẩu tài khoản người dùng và gửi email cảnh báo bảo mật."""
    service = UsersService(db)
    result = await service.change_password(current_user, payload, background_tasks)
    return ApiResponse(data=result, message=result["message"])


# ==========================================
# Admin User Controls
# ==========================================


@router.get(
    "/admin/users",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedResponse[AdminUserItem],
    summary="Lấy danh sách học viên (Admin)",
    tags=["admin-users"],
)
async def list_admin_users(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(20, ge=1, le=100, description="Số lượng bản ghi mỗi trang"),
    search: str | None = Query(None, description="Tìm theo họ tên hoặc email"),
    status: Literal["active", "locked", "unverified"] | None = Query(
        None, description="Lọc theo trạng thái tài khoản"
    ),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[AdminUserItem]:
    """Lấy danh sách người dùng/học viên kèm số lượng khóa học đã đăng ký cho Admin."""
    service = UsersService(db)
    return await service.list_admin_users(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
    )


@router.put(
    "/admin/users/{user_id}/lock",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[LockUserResponse],
    summary="Khóa tài khoản học viên (Admin)",
    tags=["admin-users"],
)
async def lock_user(
    user_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[LockUserResponse]:
    """Khóa tài khoản học viên, tự động thu hồi session/refresh token và gửi email thông báo."""
    service = UsersService(db)
    result = await service.lock_user(current_user, user_id, background_tasks)
    return ApiResponse(data=result, message=result.message)


@router.put(
    "/admin/users/{user_id}/unlock",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[LockUserResponse],
    summary="Mở khóa tài khoản học viên (Admin)",
    tags=["admin-users"],
)
async def unlock_user(
    user_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[LockUserResponse]:
    """Mở khóa tài khoản học viên và gửi email thông báo."""
    service = UsersService(db)
    result = await service.unlock_user(current_user, user_id, background_tasks)
    return ApiResponse(data=result, message=result.message)
