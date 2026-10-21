"""Users data access layer."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import Enrollment, RefreshToken, User


class UsersRepository:
    """Repository handling database operations for users and credentials."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Fetch a non-deleted user by primary key."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_profile(
        self,
        user_id: UUID,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        """Update full_name and/or avatar_url for a given user."""
        values: dict[str, object] = {"updated_at": func.now()}
        if full_name is not None:
            values["full_name"] = full_name
        if avatar_url is not None:
            values["avatar_url"] = avatar_url

        stmt = (
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(**values)
            .returning(User)
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one()
        return user

    async def update_password(self, user_id: UUID, password_hash: str) -> None:
        """Update password hash for a given user."""
        stmt = (
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(password_hash=password_hash, updated_at=func.now())
        )
        await self.db.execute(stmt)

    async def list_users_for_admin(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[tuple[User, int]], int]:
        """List users with pagination, filters, and enrolled courses count."""
        conditions = [User.deleted_at.is_(None)]

        if search:
            search_pattern = f"%{search.strip()}%"
            conditions.append(
                or_(
                    User.full_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )

        if status == "active":
            conditions.extend([User.is_verified.is_(True), User.is_locked.is_(False)])
        elif status == "locked":
            conditions.append(User.is_locked.is_(True))
        elif status == "unverified":
            conditions.append(User.is_verified.is_(False))

        # Subquery to count enrollments per user
        enrollment_count_subquery = (
            select(func.count(Enrollment.id))
            .where(Enrollment.user_id == User.id)
            .correlate(User)
            .scalar_subquery()
        )

        # Count total records matching filters
        count_stmt = select(func.count(User.id)).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Query paginated results
        query = (
            select(User, func.coalesce(enrollment_count_subquery, 0).label("enrolled_courses_count"))
            .where(*conditions)
            .order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        rows = result.all()
        items = [(row[0], int(row[1])) for row in rows]
        return items, total

    async def set_lock_status(self, user_id: UUID, is_locked: bool) -> User | None:
        """Update is_locked status of a user."""
        stmt = (
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(is_locked=is_locked, updated_at=func.now())
            .returning(User)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_all_user_tokens(self, user_id: UUID) -> None:
        """Revoke all active refresh tokens for the given user."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )
        await self.db.execute(stmt)
