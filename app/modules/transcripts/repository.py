"""Transcripts data access repository (Spec 09 §3.3, §5.4)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.ai.whisper import WhisperSegmentResult
from app.db.models.schema import Transcript, TranscriptSegment


class TranscriptRepository:
    """Manages persistence and retrieval of lesson transcripts and subtitle segments."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_lesson_id(self, lesson_id: UUID) -> Transcript | None:
        """Fetch transcript record by unique lesson identifier."""
        stmt = select(Transcript).where(Transcript.lesson_id == lesson_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_video_id(self, video_id: UUID) -> Transcript | None:
        """Fetch transcript record associated with a given video."""
        stmt = select(Transcript).where(Transcript.video_id == video_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_segments_by_transcript_id(self, transcript_id: UUID) -> list[TranscriptSegment]:
        """Fetch ordered segments for a transcript."""
        stmt = (
            select(TranscriptSegment)
            .where(TranscriptSegment.transcript_id == transcript_id)
            .order_by(TranscriptSegment.segment_index.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def save_transcription(
        self,
        *,
        lesson_id: UUID,
        video_id: UUID | None,
        language: str = "vi",
        segments: list[WhisperSegmentResult],
    ) -> Transcript:
        """Idempotently save transcript and its segments (Spec 09 §3.3, Spec 11 §5).

        If a transcript already exists for this lesson, it is updated and existing
        segments are cleanly replaced, preventing unique constraint violations.
        """
        now = datetime.now(timezone.utc)
        existing = await self.get_by_lesson_id(lesson_id)

        if existing:
            transcript = existing
            transcript.video_id = video_id
            transcript.language = language
            transcript.updated_at = now
            # Clean up existing segments before inserting refreshed ones (idempotency)
            del_stmt = delete(TranscriptSegment).where(TranscriptSegment.transcript_id == transcript.id)
            await self.db.execute(del_stmt)
        else:
            transcript = Transcript(
                id=uuid4(),
                lesson_id=lesson_id,
                video_id=video_id,
                language=language,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.db.add(transcript)
            await self.db.flush()

        # Bulk insert segment records ensuring constraints: end_time > start_time and start_time >= 0
        segment_records: list[TranscriptSegment] = []
        for idx, seg in enumerate(segments):
            start = max(0.0, float(seg.start_time))
            end = float(seg.end_time)
            if end <= start:
                end = round(start + 0.1, 2)

            segment_records.append(
                TranscriptSegment(
                    id=uuid4(),
                    transcript_id=transcript.id,
                    segment_index=idx,
                    start_time=round(start, 2),
                    end_time=round(end, 2),
                    text=seg.text.strip(),
                    created_at=now,
                )
            )

        if segment_records:
            self.db.add_all(segment_records)

        await self.db.flush()
        return transcript
