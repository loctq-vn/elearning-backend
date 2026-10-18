"""Authentication business services."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.mailer import mailer
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.models.schema import OtpPurpose, User, UserRole
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    AuthUserResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    ResendOtpRequest,
    ResendOtpResponse,
    ResetPasswordRequest,
    VerifyOtpRequest,
    VerifyOtpResponse,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service implementing authentication workflows."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuthRepository(db)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _generate_otp() -> str:
        return f"{secrets.randbelow(1000000):06d}"

    async def register(self, payload: RegisterRequest) -> RegisterResponse:
        """Register a new student account and dispatch OTP."""
        email = payload.email.strip().lower()
        existing_user = await self.repo.get_user_by_email(email)

        if existing_user:
            if existing_user.is_verified:
                raise AppError(
                    status_code=409,
                    code="EMAIL_ALREADY_EXISTS",
                    message="Email này đã được đăng ký. Vui lòng đăng nhập.",
                )
            # Unverified account re-attempting registration: update info
            password_hash = get_password_hash(payload.password)
            await self.repo.update_user(
                existing_user,
                full_name=payload.full_name,
                password_hash=password_hash,
            )
        else:
            password_hash = get_password_hash(payload.password)
            await self.repo.create_user(
                full_name=payload.full_name,
                email=email,
                password_hash=password_hash,
                role=UserRole.STUDENT,
                is_verified=False,
            )

        # Invalidate any pending registration OTPs
        await self.repo.invalidate_pending_otps(email, OtpPurpose.REGISTRATION)

        # Generate fresh OTP
        otp_code = self._generate_otp()
        code_hash = self._hash_token(otp_code)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)

        await self.repo.create_otp(
            email=email,
            purpose=OtpPurpose.REGISTRATION,
            code_hash=code_hash,
            expires_at=expires_at,
        )

        try:
            await mailer.send_otp_email(
                to_email=email,
                otp_code=otp_code,
                purpose="registration",
                expires_in_seconds=300,
            )
        except Exception as exc:
            logger.error("Failed to dispatch registration OTP email to %s: %s", email, exc)
            if settings.app_env in {"staging", "production"} and mailer.is_configured:
                raise AppError(
                    status_code=500,
                    code="EMAIL_SEND_FAILED",
                    message="Không thể gửi email chứa mã xác nhận. Vui lòng thử lại sau.",
                )

        await self.db.commit()

        return RegisterResponse(
            message="Đăng ký thành công. Mã OTP đã gửi đến email.",
            email=email,
            otp_expires_in=300,
        )

    async def verify_otp(self, payload: VerifyOtpRequest) -> VerifyOtpResponse:
        """Verify an OTP code for either registration or password reset."""
        email = payload.email.strip().lower()
        purpose = (
            OtpPurpose.REGISTRATION
            if payload.purpose == "registration"
            else OtpPurpose.PASSWORD_RESET
        )

        otp_record = await self.repo.get_latest_otp(email, purpose)
        if not otp_record:
            raise AppError(
                status_code=400,
                code="INVALID_OTP",
                message="Mã xác nhận không đúng.",
            )

        if otp_record.attempt_count >= 5:
            raise AppError(
                status_code=429,
                code="OTP_ATTEMPTS_EXCEEDED",
                message="Bạn đã nhập sai quá nhiều lần. Thử lại sau 15 phút.",
            )

        if otp_record.expires_at < datetime.now(timezone.utc):
            raise AppError(
                status_code=400,
                code="OTP_EXPIRED",
                message="Mã đã hết hạn. Vui lòng bấm gửi lại mã.",
            )

        input_hash = self._hash_token(payload.otp_code)
        if input_hash != otp_record.code_hash:
            attempts = await self.repo.increment_otp_attempts(otp_record)
            await self.db.commit()
            if attempts >= 5:
                raise AppError(
                    status_code=429,
                    code="OTP_ATTEMPTS_EXCEEDED",
                    message="Bạn đã nhập sai quá nhiều lần. Thử lại sau 15 phút.",
                )
            raise AppError(
                status_code=400,
                code="INVALID_OTP",
                message="Mã xác nhận không đúng.",
            )

        # Mark OTP as successfully used
        await self.repo.mark_otp_used(otp_record)

        if purpose == OtpPurpose.REGISTRATION:
            user = await self.repo.get_user_by_email(email)
            if not user:
                raise AppError(
                    status_code=400,
                    code="INVALID_OTP",
                    message="Tài khoản không tồn tại.",
                )

            await self.repo.update_user(user, is_verified=True)

            # Auto-login upon successful registration verification
            access_token = create_access_token(
                subject=user.id,
                extra_claims={"role": user.role.value, "email": user.email},
            )
            refresh_token = create_refresh_token(subject=user.id)
            rf_hash = self._hash_token(refresh_token)
            rf_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

            await self.repo.create_refresh_token(
                user_id=user.id,
                token_hash=rf_hash,
                expires_at=rf_expires,
            )
            await self.db.commit()

            return VerifyOtpResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="Bearer",
                expires_in=settings.access_token_expire_seconds,
                reset_token=None,
            )

        # Purpose is PASSWORD_RESET
        user = await self.repo.get_user_by_email(email)
        if not user:
            raise AppError(
                status_code=400,
                code="INVALID_OTP",
                message="Tài khoản không tồn tại.",
            )

        reset_token = create_reset_token(subject=user.id, extra_claims={"email": user.email})
        await self.db.commit()

        return VerifyOtpResponse(
            access_token=None,
            refresh_token=None,
            token_type=None,
            expires_in=None,
            reset_token=reset_token,
        )

    async def resend_otp(self, payload: ResendOtpRequest) -> ResendOtpResponse:
        """Resend a new OTP with cooldown enforcement."""
        email = payload.email.strip().lower()
        purpose = (
            OtpPurpose.REGISTRATION
            if payload.purpose == "registration"
            else OtpPurpose.PASSWORD_RESET
        )

        user = await self.repo.get_user_by_email(email)
        if purpose == OtpPurpose.REGISTRATION:
            if not user:
                raise AppError(
                    status_code=404,
                    code="NOT_FOUND",
                    message="Email chưa được đăng ký.",
                )
            if user.is_verified:
                raise AppError(
                    status_code=400,
                    code="ALREADY_VERIFIED",
                    message="Tài khoản đã được xác thực.",
                )

        # Rate limit cooldown check (60 seconds)
        latest_otp = await self.repo.get_latest_otp(email, purpose)
        if latest_otp:
            elapsed = (datetime.now(timezone.utc) - latest_otp.created_at).total_seconds()
            if elapsed < 60:
                raise AppError(
                    status_code=429,
                    code="RESEND_COOLDOWN",
                    message=f"Vui lòng chờ {int(60 - elapsed)} giây trước khi gửi lại mã.",
                )

        await self.repo.invalidate_pending_otps(email, purpose)

        # If user exists (or in registration flow), issue and dispatch OTP
        if user or purpose == OtpPurpose.REGISTRATION:
            otp_code = self._generate_otp()
            code_hash = self._hash_token(otp_code)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)

            await self.repo.create_otp(
                email=email,
                purpose=purpose,
                code_hash=code_hash,
                expires_at=expires_at,
            )

            try:
                await mailer.send_otp_email(
                    to_email=email,
                    otp_code=otp_code,
                    purpose=payload.purpose,
                    expires_in_seconds=300,
                )
            except Exception as exc:
                logger.error("Failed to resend OTP email to %s: %s", email, exc)
                if settings.app_env in {"staging", "production"} and mailer.is_configured:
                    raise AppError(
                        status_code=500,
                        code="EMAIL_SEND_FAILED",
                        message="Không thể gửi lại mã OTP. Vui lòng thử lại sau.",
                    )

        await self.db.commit()

        return ResendOtpResponse(
            message="Mã OTP mới đã được gửi.",
            otp_expires_in=300,
        )

    async def login(self, payload: LoginRequest) -> LoginResponse:
        """Authenticate user credentials and issue token pair."""
        email = payload.email.strip().lower()
        user = await self.repo.get_user_by_email(email)

        if not user or not verify_password(payload.password, user.password_hash):
            raise AppError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Email hoặc mật khẩu không đúng.",
            )

        if user.is_locked:
            raise AppError(
                status_code=403,
                code="ACCOUNT_LOCKED",
                message="Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.",
            )

        if not user.is_verified:
            raise AppError(
                status_code=403,
                code="EMAIL_NOT_VERIFIED",
                message="Tài khoản chưa được xác thực email. Vui lòng xác thực tài khoản.",
            )

        access_token = create_access_token(
            subject=user.id,
            extra_claims={"role": user.role.value, "email": user.email},
        )
        refresh_token = create_refresh_token(subject=user.id)
        rf_hash = self._hash_token(refresh_token)
        rf_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        await self.repo.create_refresh_token(
            user_id=user.id,
            token_hash=rf_hash,
            expires_at=rf_expires,
        )
        await self.db.commit()

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_seconds,
            user=AuthUserResponse(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                avatar_url=user.avatar_url,
                role=user.role.value,
            ),
        )

    async def refresh_tokens(self, payload: RefreshTokenRequest) -> RefreshTokenResponse:
        """Perform refresh token rotation."""
        try:
            token_data = decode_token(payload.refresh_token, expected_type="refresh")
        except AppError:
            raise AppError(
                status_code=401,
                code="REFRESH_TOKEN_INVALID",
                message="Token không hợp lệ hoặc đã hết hạn.",
            )

        user_id_str = token_data.get("sub")
        if not user_id_str:
            raise AppError(
                status_code=401,
                code="REFRESH_TOKEN_INVALID",
                message="Token không hợp lệ.",
            )

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise AppError(
                status_code=401,
                code="REFRESH_TOKEN_INVALID",
                message="Mã định danh không hợp lệ.",
            )

        rf_hash = self._hash_token(payload.refresh_token)
        token_record = await self.repo.get_refresh_token(rf_hash)
        if not token_record or token_record.expires_at < datetime.now(timezone.utc):
            raise AppError(
                status_code=401,
                code="REFRESH_TOKEN_INVALID",
                message="Token không hợp lệ hoặc đã bị thu hồi.",
            )

        user = await self.repo.get_user_by_id(user_id)
        if not user or user.is_locked:
            raise AppError(
                status_code=401,
                code="UNAUTHORIZED",
                message="Tài khoản không tồn tại hoặc đã bị khóa.",
            )

        # Rotate: revoke current and issue new pair
        await self.repo.revoke_refresh_token(token_record)

        new_access_token = create_access_token(
            subject=user.id,
            extra_claims={"role": user.role.value, "email": user.email},
        )
        new_refresh_token = create_refresh_token(subject=user.id)
        new_rf_hash = self._hash_token(new_refresh_token)
        new_rf_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        await self.repo.create_refresh_token(
            user_id=user.id,
            token_hash=new_rf_hash,
            expires_at=new_rf_expires,
        )
        await self.db.commit()

        return RefreshTokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_seconds,
        )

    async def logout(self, current_user: User, payload: LogoutRequest | None = None) -> MessageResponse:
        """Revoke refresh token session."""
        if payload and payload.refresh_token:
            rf_hash = self._hash_token(payload.refresh_token)
            token_record = await self.repo.get_refresh_token(rf_hash)
            if token_record:
                await self.repo.revoke_refresh_token(token_record)
        else:
            await self.repo.revoke_all_user_refresh_tokens(current_user.id)

        await self.db.commit()
        return MessageResponse(message="Đăng xuất thành công")

    async def forgot_password(self, payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
        """Send password reset OTP. Always responds 200 for security."""
        email = payload.email.strip().lower()
        user = await self.repo.get_user_by_email(email)

        if user and not user.is_locked:
            latest_otp = await self.repo.get_latest_otp(email, OtpPurpose.PASSWORD_RESET)
            allow_send = True
            if latest_otp:
                elapsed = (datetime.now(timezone.utc) - latest_otp.created_at).total_seconds()
                if elapsed < 60:
                    allow_send = False

            if allow_send:
                await self.repo.invalidate_pending_otps(email, OtpPurpose.PASSWORD_RESET)

                otp_code = self._generate_otp()
                code_hash = self._hash_token(otp_code)
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)

                await self.repo.create_otp(
                    email=email,
                    purpose=OtpPurpose.PASSWORD_RESET,
                    code_hash=code_hash,
                    expires_at=expires_at,
                )

                try:
                    await mailer.send_otp_email(
                        to_email=email,
                        otp_code=otp_code,
                        purpose="password_reset",
                        expires_in_seconds=300,
                    )
                except Exception as exc:
                    logger.error("Failed to send password reset OTP email to %s: %s", email, exc)

                await self.db.commit()

        return ForgotPasswordResponse(
            message="Nếu email tồn tại, mã xác nhận sẽ được gửi.",
            otp_expires_in=300,
        )

    async def reset_password(self, payload: ResetPasswordRequest) -> MessageResponse:
        """Update password using a verified reset token."""
        try:
            token_data = decode_token(payload.reset_token, expected_type="password_reset")
        except AppError:
            raise AppError(
                status_code=400,
                code="INVALID_RESET_TOKEN",
                message="Liên kết đặt lại đã hết hạn hoặc không hợp lệ. Vui lòng thử lại.",
            )

        user_id_str = token_data.get("sub")
        if not user_id_str:
            raise AppError(
                status_code=400,
                code="INVALID_RESET_TOKEN",
                message="Token không hợp lệ.",
            )

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise AppError(
                status_code=400,
                code="INVALID_RESET_TOKEN",
                message="Token không hợp lệ.",
            )

        user = await self.repo.get_user_by_id(user_id)
        if not user or user.is_locked:
            raise AppError(
                status_code=400,
                code="INVALID_RESET_TOKEN",
                message="Tài khoản không hợp lệ hoặc đã bị khóa.",
            )

        new_hash = get_password_hash(payload.new_password)
        await self.repo.update_user(user, password_hash=new_hash, is_verified=True)

        # Invalidate all prior active sessions
        await self.repo.revoke_all_user_refresh_tokens(user.id)
        await self.db.commit()

        return MessageResponse(message="Mật khẩu đã được đặt lại thành công.")
