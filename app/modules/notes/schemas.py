"""Notes request and response schemas (Doc 08 §7)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteItemOut(BaseModel):
    """Note item schema (§7.1, §7.3)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    timestamp: float
    created_at: datetime
    updated_at: datetime


class NoteListResponse(BaseModel):
    """List of notes response schema (§7.1)."""

    data: list[NoteItemOut]


class NoteCreateIn(BaseModel):
    """Create note request schema (§7.2)."""

    content: str = Field(..., min_length=1, max_length=2000, description="Nội dung, 1–2000 ký tự")
    timestamp: float = Field(..., ge=0, description="Mốc thời gian video hiện tại (giây)")


class NoteCreateOut(BaseModel):
    """Create note response schema (§7.2)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    timestamp: float
    created_at: datetime


class NoteUpdateIn(BaseModel):
    """Update note request schema (§7.3)."""

    content: str = Field(
        ..., min_length=1, max_length=2000, description="Nội dung mới, 1–2000 ký tự"
    )


class NoteDeleteResponse(BaseModel):
    """Delete note response schema (§7.4)."""

    message: str = "Đã xóa ghi chú."
