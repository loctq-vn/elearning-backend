"""Transcripts business services (Spec 09 §3.3, §5.4, Spec 11 §5)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.ai.whisper import WhisperSegmentResult
from app.modules.transcripts.repository import TranscriptRepository
from app.modules.transcripts.schemas import (
    TranscriptResponse,
    TranscriptSegmentResponse,
)


class TranscriptService:
    """Coordinates transcript queries and persistence operations."""

    def __init__(self, db: AsyncSession, repo: TranscriptRepository | None = None) -> None:
        self.db = db
        self.repo = repo or TranscriptRepository(db)

    async def get_transcript_for_lesson(self, lesson_id: UUID) -> TranscriptResponse | None:
        """Retrieve full transcript and segments for a lesson."""
        transcript = await self.repo.get_by_lesson_id(lesson_id)
        if not transcript:
            return None

        segments = await self.repo.get_segments_by_transcript_id(transcript.id)
        segment_dtos = [TranscriptSegmentResponse.model_validate(seg) for seg in segments]

        return TranscriptResponse(
            id=transcript.id,
            lesson_id=transcript.lesson_id,
            video_id=transcript.video_id,
            language=transcript.language,
            version=transcript.version,
            created_at=transcript.created_at,
            updated_at=transcript.updated_at,
            segments=segment_dtos,
        )

    async def save_initial_transcription(
        self,
        *,
        lesson_id: UUID,
        video_id: UUID | None,
        language: str = "vi",
        segments: list[WhisperSegmentResult],
    ) -> TranscriptResponse:
        """Persist newly generated transcript segments and return response DTO."""
        transcript = await self.repo.save_transcription(
            lesson_id=lesson_id,
            video_id=video_id,
            language=language,
            segments=segments,
        )
        await self.db.commit()
        return await self.get_transcript_for_lesson(transcript.lesson_id)  # type: ignore[return-value]
