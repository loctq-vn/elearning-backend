"""Tests for Transcript Persistence and Repository (Phase D1.04, Spec 09 §3.3, §5.4)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.adapters.ai.whisper import WhisperSegmentResult
from app.db.models.schema import (
    Category,
    Chapter,
    Course,
    CourseStatus,
    Lesson,
    Transcript,
    TranscriptSegment,
    User,
    UserRole,
    Video,
    VideoOverallStatus,
)
from app.db.session import async_session_factory
from app.modules.transcripts.repository import TranscriptRepository
from app.modules.transcripts.service import TranscriptService


async def _create_test_lesson_and_video() -> tuple[Lesson, Video]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        user = User(
            id=uuid4(),
            full_name="Transcript Tester",
            email=f"transcript_test_{suffix}@example.com",
            password_hash="fakehash",
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.flush()

        cat = Category(name=f"Trans Cat {suffix}", slug=f"trans-cat-{suffix}")
        session.add(cat)
        await session.flush()

        course = Course(
            title=f"Trans Course {suffix}",
            category_id=cat.id,
            price=0,
            status=CourseStatus.DRAFT,
            created_by=user.id,
        )
        session.add(course)
        await session.flush()

        chapter = Chapter(
            title=f"Trans Chapter {suffix}",
            course_id=course.id,
            order_index=1,
        )
        session.add(chapter)
        await session.flush()

        lesson = Lesson(
            title=f"Trans Lesson {suffix}",
            chapter_id=chapter.id,
            course_id=course.id,
            order_index=1,
            is_trial_allowed=True,
        )
        session.add(lesson)
        await session.flush()

        video = Video(
            id=uuid4(),
            lesson_id=lesson.id,
            original_filename="sample.mp4",
            file_size_bytes=1024 * 1024,
            mime_type="video/mp4",
            overall_status=VideoOverallStatus.PROCESSING,
        )
        session.add(video)
        await session.commit()
        return lesson, video


@pytest.mark.asyncio
async def test_save_transcription_and_query() -> None:
    """Spec 09 §3.3: Verify saving transcript and segments to RDS."""
    lesson, video = await _create_test_lesson_and_video()

    segments = [
        WhisperSegmentResult(segment_index=0, start_time=0.0, end_time=2.45, text="Đoạn mở đầu"),
        WhisperSegmentResult(segment_index=1, start_time=2.45, end_time=5.80, text="Nội dung chính"),
        WhisperSegmentResult(segment_index=2, start_time=5.80, end_time=10.12, text="Tổng kết bài học"),
    ]

    async with async_session_factory() as session:
        repo = TranscriptRepository(session)
        transcript = await repo.save_transcription(
            lesson_id=lesson.id,
            video_id=video.id,
            language="vi",
            segments=segments,
        )
        await session.commit()
        t_id = transcript.id

    assert transcript.lesson_id == lesson.id
    assert transcript.video_id == video.id
    assert transcript.version == 1
    assert transcript.language == "vi"

    # Query via Service
    async with async_session_factory() as session:
        service = TranscriptService(session)
        dto = await service.get_transcript_for_lesson(lesson.id)

    assert dto is not None
    assert dto.id == t_id
    assert len(dto.segments) == 3
    assert dto.segments[0].segment_index == 0
    assert dto.segments[0].text == "Đoạn mở đầu"
    assert dto.segments[1].segment_index == 1
    assert dto.segments[1].start_time == 2.45
    assert dto.segments[2].end_time == 10.12


@pytest.mark.asyncio
async def test_transcription_idempotency_on_retry() -> None:
    """Spec 11 §11: Re-running transcribe step cleanly replaces existing segments."""
    lesson, video = await _create_test_lesson_and_video()

    initial_segments = [
        WhisperSegmentResult(segment_index=0, start_time=0.0, end_time=3.0, text="Bản nháp 1"),
        WhisperSegmentResult(segment_index=1, start_time=3.0, end_time=6.0, text="Bản nháp 2"),
    ]

    refreshed_segments = [
        WhisperSegmentResult(segment_index=0, start_time=0.0, end_time=4.0, text="Bản chính thức 1"),
        WhisperSegmentResult(segment_index=1, start_time=4.0, end_time=8.5, text="Bản chính thức 2"),
        WhisperSegmentResult(segment_index=2, start_time=8.5, end_time=12.0, text="Bản chính thức 3"),
    ]

    async with async_session_factory() as session:
        repo = TranscriptRepository(session)
        await repo.save_transcription(
            lesson_id=lesson.id,
            video_id=video.id,
            language="vi",
            segments=initial_segments,
        )
        await session.commit()

    # Re-run / retry saving with refreshed segments
    async with async_session_factory() as session:
        repo = TranscriptRepository(session)
        updated = await repo.save_transcription(
            lesson_id=lesson.id,
            video_id=video.id,
            language="vi",
            segments=refreshed_segments,
        )
        await session.commit()

    async with async_session_factory() as session:
        repo = TranscriptRepository(session)
        segments_in_db = await repo.get_segments_by_transcript_id(updated.id)

    assert len(segments_in_db) == 3
    assert [s.text for s in segments_in_db] == [
        "Bản chính thức 1",
        "Bản chính thức 2",
        "Bản chính thức 3",
    ]
