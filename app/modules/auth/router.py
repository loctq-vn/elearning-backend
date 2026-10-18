"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models.schema import User
from app.db.session import get_db_session
from app.modules.auth.schemas import (
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
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    summary="Đăng ký tài khoản học viên mới",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RegisterResponse:
    """Học viên đăng ký tài khoản mới và nhận mã OTP qua email."""
    service = AuthService(db)
    return await service.register(payload)


@router.post(
    "/verify-otp",
    status_code=status.HTTP_200_OK,
    response_model=VerifyOtpResponse,
    summary="Xác thực mã OTP",
)
async def verify_otp(
    payload: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db_session),
) -> VerifyOtpResponse:
    """Xác thực OTP cho đăng ký tài khoản (auto-login) hoặc quên mật khẩu."""
    service = AuthService(db)
    return await service.verify_otp(payload)


@router.post(
    "/resend-otp",
    status_code=status.HTTP_200_OK,
    response_model=ResendOtpResponse,
    summary="Gửi lại mã OTP",
)
async def resend_otp(
    payload: ResendOtpRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ResendOtpResponse:
    """Gửi lại mã OTP mới với giới hạn thời gian chờ (cooldown 60s)."""
    service = AuthService(db)
    return await service.resend_otp(payload)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=LoginResponse,
    summary="Đăng nhập",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    """Đăng nhập bằng email và mật khẩu."""
    service = AuthService(db)
    return await service.login(payload)


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=RefreshTokenResponse,
    summary="Làm mới token (Refresh token)",
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RefreshTokenResponse:
    """Làm mới Access Token và Refresh Token theo cơ chế Token Rotation."""
    service = AuthService(db)
    return await service.refresh_tokens(payload)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Đăng xuất",
)
async def logout(
    payload: LogoutRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Đăng xuất và thu hồi Refresh Token."""
    service = AuthService(db)
    return await service.logout(current_user=current_user, payload=payload)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    response_model=ForgotPasswordResponse,
    summary="Yêu cầu đặt lại mật khẩu",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ForgotPasswordResponse:
    """Yêu cầu gửi mã OTP để đặt lại mật khẩu qua email."""
    service = AuthService(db)
    return await service.forgot_password(payload)


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Đặt lại mật khẩu mới",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Đặt lại mật khẩu mới bằng reset_token nhận từ bước xác thực OTP."""
    service = AuthService(db)
    return await service.reset_password(payload)
