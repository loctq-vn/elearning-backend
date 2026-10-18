"""Authentication request and response schemas."""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validate_password_strength(password: str) -> str:
    """Validate that password meets complexity requirements."""
    if len(password) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự.")
    if not any(c.isupper() for c in password):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ in hoa.")
    if not any(c.islower() for c in password):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ thường.")
    if not any(c.isdigit() for c in password):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số.")
    if not any(not c.isalnum() for c in password):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt.")
    return password


class RegisterRequest(BaseModel):
    """Payload for POST /api/auth/register."""

    full_name: str = Field(..., min_length=2, max_length=100, description="Họ và tên người dùng")
    email: EmailStr = Field(..., max_length=255, description="Email hợp lệ")
    password: str = Field(..., min_length=8, description="Mật khẩu bảo mật")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 2 or len(trimmed) > 100:
            raise ValueError("Họ tên phải có độ dài từ 2 đến 100 ký tự.")
        return trimmed

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class RegisterResponse(BaseModel):
    """Response for POST /api/auth/register."""

    message: str = "Đăng ký thành công. Mã OTP đã gửi đến email."
    email: str
    otp_expires_in: int = 300


class VerifyOtpRequest(BaseModel):
    """Payload for POST /api/auth/verify-otp."""

    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6, description="Mã 6 chữ số")
    purpose: Literal["registration", "password_reset"]

    @field_validator("otp_code")
    @classmethod
    def validate_otp_code(cls, value: str) -> str:
        clean = value.strip()
        if not re.fullmatch(r"^\d{6}$", clean):
            raise ValueError("Mã OTP phải gồm đúng 6 chữ số.")
        return clean


class VerifyOtpResponse(BaseModel):
    """Response for POST /api/auth/verify-otp."""

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    reset_token: str | None = None


class ResendOtpRequest(BaseModel):
    """Payload for POST /api/auth/resend-otp."""

    email: EmailStr
    purpose: Literal["registration", "password_reset"]


class ResendOtpResponse(BaseModel):
    """Response for POST /api/auth/resend-otp."""

    message: str = "Mã OTP mới đã được gửi."
    otp_expires_in: int = 300


class LoginRequest(BaseModel):
    """Payload for POST /api/auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class AuthUserResponse(BaseModel):
    """Authenticated user info."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    avatar_url: str | None = None
    role: str


class LoginResponse(BaseModel):
    """Response for POST /api/auth/login."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900
    user: AuthUserResponse


class RefreshTokenRequest(BaseModel):
    """Payload for POST /api/auth/refresh."""

    refresh_token: str = Field(..., min_length=1)


class RefreshTokenResponse(BaseModel):
    """Response for POST /api/auth/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900


class LogoutRequest(BaseModel):
    """Payload for POST /api/auth/logout."""

    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    """Payload for POST /api/auth/forgot-password."""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Response for POST /api/auth/forgot-password."""

    message: str = "Nếu email tồn tại, mã xác nhận sẽ được gửi."
    otp_expires_in: int = 300


class ResetPasswordRequest(BaseModel):
    """Payload for POST /api/auth/reset-password."""

    reset_token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
