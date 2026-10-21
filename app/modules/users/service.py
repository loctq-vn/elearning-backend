"""Users business services."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.mailer import MailerAdapter, mailer
from app.adapters.storage import S3StorageAdapter, user_avatar_key
from app.core.config import settings
from app.core.errors import AppError
from app.core.schemas import PaginatedResponse, build_paginated_response
from app.core.security import get_password_hash, verify_password
from app.db.models.schema import User, UserRole
from app.modules.users.repository import UsersRepository
from app.modules.users.schemas import (
    AdminUserItem,
    ChangePasswordRequest,
    LockUserResponse,
    UserProfileResponse,
)

logger = logging.getLogger(__name__)

ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024  # 2MB


def validate_password_complexity(password: str) -> None:
    """Ensure password meets security policy requirements."""
    if (
        len(password) < 8
        or not any(c.isupper() for c in password)
        or not any(c.islower() for c in password)
        or not any(c.isdigit() for c in password)
        or not any(not c.isalnum() for c in password)
    ):
        raise AppError(
            status_code=400,
            code="PASSWORD_TOO_WEAK",
            message="Mật khẩu mới quá yếu. Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt.",
        )


async def send_email_safe(
    mailer_instance: MailerAdapter,
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> None:
    """Send email in background without raising exceptions into the API."""
    try:
        await mailer_instance.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
    except Exception:
        logger.exception("Failed to send background email to %s: %s", to_email, subject)


class UsersService:
    """Service handling user profile, password modification, and admin user management."""

    def __init__(
        self,
        db: AsyncSession,
        storage: S3StorageAdapter | None = None,
        email_sender: MailerAdapter | None = None,
    ) -> None:
        self.db = db
        self.repo = UsersRepository(db)
        self.storage = storage or S3StorageAdapter(settings)
        self.mailer = email_sender or mailer

    @staticmethod
    def _to_profile_response(user: User) -> UserProfileResponse:
        role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
        return UserProfileResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            avatar_url=user.avatar_url,
            role=role_value,
            created_at=user.created_at,
        )

    async def get_me(self, current_user: User) -> UserProfileResponse:
        """Get profile of current authenticated user."""
        return self._to_profile_response(current_user)

    async def update_profile(
        self,
        current_user: User,
        full_name: str | None = None,
        avatar: UploadFile | None = None,
    ) -> UserProfileResponse:
        """Update profile information including full name and avatar upload."""
        trimmed_name: str | None = None
        if full_name is not None:
            trimmed_name = full_name.strip()
            if len(trimmed_name) < 2 or len(trimmed_name) > 100:
                raise AppError(
                    status_code=400,
                    code="VALIDATION_ERROR",
                    message="Họ tên phải có độ dài từ 2 đến 100 ký tự.",
                )

        new_avatar_url: str | None = None
        if avatar is not None and avatar.filename:
            content_type = avatar.content_type or ""
            if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
                raise AppError(
                    status_code=400,
                    code="INVALID_FILE_TYPE",
                    message="Ảnh đại diện chỉ chấp nhận định dạng JPEG, PNG hoặc WebP.",
                )

            avatar_bytes = await avatar.read()
            if len(avatar_bytes) > MAX_AVATAR_SIZE_BYTES:
                raise AppError(
                    status_code=400,
                    code="FILE_TOO_LARGE",
                    message="Dung lượng ảnh đại diện không được vượt quá 2MB.",
                )

            extension = ALLOWED_AVATAR_CONTENT_TYPES[content_type]
            filename = f"avatar_{uuid4().hex[:8]}.{extension}"
            key = user_avatar_key(str(current_user.id), filename)

            new_avatar_url = self.storage.upload_file(
                file_bytes=avatar_bytes,
                key=key,
                content_type=content_type,
            )

        updated_user = await self.repo.update_profile(
            user_id=current_user.id,
            full_name=trimmed_name,
            avatar_url=new_avatar_url,
        )
        await self.db.commit()
        await self.db.refresh(updated_user)
        return self._to_profile_response(updated_user)

    async def change_password(
        self,
        current_user: User,
        payload: ChangePasswordRequest,
        background_tasks: BackgroundTasks,
    ) -> dict[str, str]:
        """Change user password with strict verification and email alert."""
        if not verify_password(payload.current_password, current_user.password_hash):
            raise AppError(
                status_code=400,
                code="WRONG_CURRENT_PASSWORD",
                message="Mật khẩu hiện tại không chính xác.",
            )

        if (
            payload.new_password == payload.current_password
            or verify_password(payload.new_password, current_user.password_hash)
        ):
            raise AppError(
                status_code=400,
                code="SAME_AS_OLD_PASSWORD",
                message="Mật khẩu mới không được trùng với mật khẩu cũ.",
            )

        validate_password_complexity(payload.new_password)

        new_password_hash = get_password_hash(payload.new_password)
        await self.repo.update_password(current_user.id, new_password_hash)
        await self.db.commit()

        # Send security alert email via background tasks
        subject = f"[{settings.app_name}] Cảnh báo bảo mật: Mật khẩu của bạn vừa được thay đổi"
        text_content = (
            f"Chào {current_user.full_name},\n\n"
            f"Mật khẩu tài khoản của bạn trên {settings.app_name} vừa được thay đổi thành công.\n"
            f"Nếu bạn không thực hiện hành động này, hãy liên hệ ngay với chúng tôi để bảo vệ tài khoản.\n\n"
            f"Trân trọng,\n"
            f"Đội ngũ {settings.app_name}"
        )
        html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #f4f6f9; padding: 24px;">
  <div style="max-width: 500px; margin: 0 auto; background: #fff; padding: 32px; border-radius: 8px;">
    <h2 style="color: #1e3a8a;">Cảnh báo bảo mật</h2>
    <p>Xin chào <strong>{current_user.full_name}</strong>,</p>
    <p>Mật khẩu tài khoản của bạn tại <strong>{settings.app_name}</strong> vừa được thay đổi thành công.</p>
    <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; margin: 20px 0;">
      <strong>Lưu ý:</strong> Nếu bạn không phải là người thực hiện yêu cầu này, vui lòng liên hệ ngay với quản trị viên để được hỗ trợ.
    </div>
    <p style="color: #6b7280; font-size: 13px;">Trân trọng,<br>Đội ngũ {settings.app_name}</p>
  </div>
</body>
</html>"""

        background_tasks.add_task(
            send_email_safe,
            self.mailer,
            current_user.email,
            subject,
            html_content,
            text_content,
        )

        return {"message": "Đổi mật khẩu thành công."}

    async def list_admin_users(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[AdminUserItem]:
        """Fetch paginated users list for administrative dashboard."""
        items, total = await self.repo.list_users_for_admin(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
        )

        admin_items = [
            AdminUserItem(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                avatar_url=user.avatar_url,
                role=user.role.value if hasattr(user.role, "value") else str(user.role),
                is_verified=user.is_verified,
                is_locked=user.is_locked,
                enrolled_courses_count=count,
                created_at=user.created_at,
            )
            for user, count in items
        ]

        return build_paginated_response(
            admin_items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def lock_user(
        self,
        admin_user: User,
        target_user_id: UUID,
        background_tasks: BackgroundTasks,
    ) -> LockUserResponse:
        """Lock student account and revoke all authentication tokens."""
        if admin_user.id == target_user_id:
            raise AppError(
                status_code=409,
                code="CANNOT_LOCK_ADMIN_SELF",
                message="Quản trị viên không thể tự khóa tài khoản của chính mình.",
            )

        target_user = await self.repo.get_by_id(target_user_id)
        if not target_user:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message="Không tìm thấy người dùng.",
            )

        role_str = (
            target_user.role.value
            if hasattr(target_user.role, "value")
            else str(target_user.role)
        )
        if role_str != UserRole.STUDENT.value:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Chỉ có thể khóa tài khoản học viên.",
            )

        await self.repo.set_lock_status(target_user_id, is_locked=True)
        await self.repo.revoke_all_user_tokens(target_user_id)
        await self.db.commit()

        # Send lock notification email in background
        subject = f"[{settings.app_name}] Thông báo: Tài khoản của bạn đã bị tạm khóa"
        text_content = (
            f"Chào {target_user.full_name},\n\n"
            f"Tài khoản của bạn trên hệ thống {settings.app_name} đã bị tạm khóa bởi Quản trị viên.\n"
            f"Nếu bạn có bất kỳ câu hỏi nào hoặc muốn khiếu nại, vui lòng liên hệ bộ phận hỗ trợ.\n\n"
            f"Trân trọng,\n"
            f"Đội ngũ {settings.app_name}"
        )
        html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #f4f6f9; padding: 24px;">
  <div style="max-width: 500px; margin: 0 auto; background: #fff; padding: 32px; border-radius: 8px;">
    <h2 style="color: #b91c1c;">Thông báo tạm khóa tài khoản</h2>
    <p>Xin chào <strong>{target_user.full_name}</strong>,</p>
    <p>Tài khoản của bạn tại <strong>{settings.app_name}</strong> đã bị tạm khóa theo quyết định của Quản trị viên.</p>
    <p>Nếu bạn cho rằng đây là một sự nhầm lẫn, vui lòng liên hệ ngay với chúng tôi để được giải quyết.</p>
    <p style="color: #6b7280; font-size: 13px;">Trân trọng,<br>Đội ngũ {settings.app_name}</p>
  </div>
</body>
</html>"""

        background_tasks.add_task(
            send_email_safe,
            self.mailer,
            target_user.email,
            subject,
            html_content,
            text_content,
        )

        return LockUserResponse(
            message="Khóa tài khoản học viên thành công.",
            user_id=target_user_id,
            is_locked=True,
        )

    async def unlock_user(
        self,
        admin_user: User,
        target_user_id: UUID,
        background_tasks: BackgroundTasks,
    ) -> LockUserResponse:
        """Unlock a previously locked student account."""
        target_user = await self.repo.get_by_id(target_user_id)
        if not target_user:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message="Không tìm thấy người dùng.",
            )

        await self.repo.set_lock_status(target_user_id, is_locked=False)
        await self.db.commit()

        # Send unlock notification email in background
        subject = f"[{settings.app_name}] Thông báo: Tài khoản của bạn đã được mở khóa"
        text_content = (
            f"Chào {target_user.full_name},\n\n"
            f"Tài khoản của bạn trên hệ thống {settings.app_name} đã được mở khóa thành công.\n"
            f"Bạn hiện có thể đăng nhập và tiếp tục học tập bình thường.\n\n"
            f"Trân trọng,\n"
            f"Đội ngũ {settings.app_name}"
        )
        html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #f4f6f9; padding: 24px;">
  <div style="max-width: 500px; margin: 0 auto; background: #fff; padding: 32px; border-radius: 8px;">
    <h2 style="color: #15803d;">Tài khoản đã được mở khóa</h2>
    <p>Xin chào <strong>{target_user.full_name}</strong>,</p>
    <p>Tài khoản của bạn tại <strong>{settings.app_name}</strong> đã được mở khóa thành công.</p>
    <p>Bạn có thể đăng nhập lại ngay bây giờ để tiếp tục tham gia các khóa học.</p>
    <p style="color: #6b7280; font-size: 13px;">Trân trọng,<br>Đội ngũ {settings.app_name}</p>
  </div>
</body>
</html>"""

        background_tasks.add_task(
            send_email_safe,
            self.mailer,
            target_user.email,
            subject,
            html_content,
            text_content,
        )

        return LockUserResponse(
            message="Mở khóa tài khoản học viên thành công.",
            user_id=target_user_id,
            is_locked=False,
        )
