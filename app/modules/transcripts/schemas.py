"""Transcripts request and response schemas (Spec 08 §2.7, §9.6, Spec 09 §3.3)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegmentResponse(BaseModel):
    """Schema for an individual timestamped subtitle segment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transcript_id: UUID
    segment_index: int = Field(..., ge=0, description="Sequential index starting at 0")
    start_time: float = Field(..., ge=0.0, description="Start time in seconds")
    end_time: float = Field(..., gt=0.0, description="End time in seconds (strictly > start_time)")
    text: str = Field(..., min_length=1, description="Transcribed text segment")
    created_at: datetime


class TranscriptResponse(BaseModel):
    """Schema for a complete lesson transcript with ordered segments."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lesson_id: UUID
    video_id: UUID | None = None
    language: str = "vi"
    version: int = 1
    created_at: datetime
    updated_at: datetime
    segments: list[TranscriptSegmentResponse] = []
