"""Users request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfileResponse(BaseModel):
    """Current user profile details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    avatar_url: str | None = None
    role: str
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    """Payload for changing authenticated user's password."""

    current_password: str = Field(..., min_length=1, description="Mật khẩu hiện tại")
    new_password: str = Field(..., min_length=1, description="Mật khẩu mới")


class AdminUserItem(BaseModel):
    """Summary item for users list in Admin portal."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    avatar_url: str | None = None
    role: str
    is_verified: bool
    is_locked: bool
    enrolled_courses_count: int = 0
    created_at: datetime


class AdminUserQueryParams(BaseModel):
    """Query parameters for admin users listing."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = None
    status: Literal["active", "locked", "unverified"] | None = None


class LockUserResponse(BaseModel):
    """Response payload when locking/unlocking a user."""

    model_config = ConfigDict(from_attributes=True)

    message: str
    user_id: UUID
    is_locked: bool
