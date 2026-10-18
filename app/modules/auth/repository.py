"""Authentication data access."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import OtpCode, OtpPurpose, RefreshToken, User, UserRole


class AuthRepository:
    """Repository handling database operations for authentication."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_email(self, email: str, include_deleted: bool = False) -> User | None:
        """Fetch user by case-insensitive email."""
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID, include_deleted: bool = False) -> User | None:
        """Fetch user by primary key."""
        stmt = select(User).where(User.id == user_id)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.STUDENT,
        is_verified: bool = False,
    ) -> User:
        """Insert a new user record."""
        user = User(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            is_verified=is_verified,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_user(self, user: User, **kwargs: object) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            setattr(user, key, value)
        await self.db.flush()
        return user

    async def get_latest_otp(self, email: str, purpose: OtpPurpose) -> OtpCode | None:
        """Fetch the most recent unused OTP for the email and purpose."""
        stmt = (
            select(OtpCode)
            .where(
                func.lower(OtpCode.email) == email.strip().lower(),
                OtpCode.purpose == purpose,
                OtpCode.used_at.is_(None),
            )
            .order_by(OtpCode.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_otp(
        self,
        *,
        email: str,
        purpose: OtpPurpose,
        code_hash: str,
        expires_at: datetime,
    ) -> OtpCode:
        """Store a new hashed OTP."""
        otp = OtpCode(
            email=email.strip().lower(),
            purpose=purpose,
            code_hash=code_hash,
            attempt_count=0,
            expires_at=expires_at,
        )
        self.db.add(otp)
        await self.db.flush()
        return otp

    async def invalidate_pending_otps(self, email: str, purpose: OtpPurpose) -> None:
        """Mark all existing unused OTPs for this email and purpose as used."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(OtpCode)
            .where(
                func.lower(OtpCode.email) == email.strip().lower(),
                OtpCode.purpose == purpose,
                OtpCode.used_at.is_(None),
            )
            .values(used_at=now)
        )
        await self.db.execute(stmt)

    async def mark_otp_used(self, otp: OtpCode) -> None:
        """Mark an OTP as consumed."""
        otp.used_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def increment_otp_attempts(self, otp: OtpCode) -> int:
        """Increment attempt count for an OTP."""
        otp.attempt_count += 1
        await self.db.flush()
        return otp.attempt_count

    async def create_refresh_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Store a refresh token hash."""
        token_record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token_record)
        await self.db.flush()
        return token_record

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        """Find an active refresh token by hash."""
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_record: RefreshToken) -> None:
        """Revoke a specific refresh token."""
        token_record.revoked_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def revoke_all_user_refresh_tokens(self, user_id: UUID) -> None:
        """Revoke all active refresh tokens for a user."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self.db.execute(stmt)
