"""Shared authentication dependencies, JWT utilities, and password hashing."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.db.models.schema import User
from app.db.session import get_db_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="JWT access token in the Authorization: Bearer <token> header.",
    auto_error=False,
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for a password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(seconds=settings.access_token_expire_seconds))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a long-lived JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.refresh_token_expire_days))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
        "type": "refresh",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_reset_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived token for password reset (default 15 minutes)."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=15))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
        "type": "password_reset",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if expected_type and token_type != expected_type:
            raise AppError(
                status_code=401,
                code="UNAUTHORIZED",
                message="Loại token không hợp lệ.",
            )
        return payload
    except ExpiredSignatureError:
        raise AppError(
            status_code=401,
            code="TOKEN_EXPIRED",
            message="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        )
    except JWTError:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Token không hợp lệ hoặc đã bị chỉnh sửa.",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Extract and authenticate the user from Authorization Bearer token."""
    if not credentials:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Vui lòng đăng nhập để tiếp tục.",
        )

    payload = decode_token(credentials.credentials, expected_type="access")
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Token không chứa thông tin định danh người dùng.",
        )

    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Mã người dùng trong token không hợp lệ.",
        )

    result = await db.execute(select(User).where(User.id == user_uuid, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Tài khoản không tồn tại hoặc đã bị xóa.",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user is active and not locked."""
    if current_user.is_locked:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên.",
        )
    return current_user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Extract user if Authorization header is present and valid, otherwise return None."""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_uuid = UUID(user_id_str)
        result = await db.execute(
            select(User).where(User.id == user_uuid, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
    except Exception:
        return None
