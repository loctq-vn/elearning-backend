"""Tests for Audio Extraction & Transcribe Worker Pipeline (Phase D1.02, D1.03, Spec 11 §4.2, §5.2)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.adapters.ai.whisper import WhisperAdapter, WhisperSegmentResult
from app.adapters.ffmpeg import FFmpegAdapter
from app.adapters.storage import S3StorageAdapter
from app.db.models.schema import (
    Category,
    Chapter,
    Course,
    CourseStatus,
    Lesson,
    PipelineStep,
    PipelineStepRecord,
    StepStatus,
    Transcript,
    User,
    UserRole,
    Video,
    VideoOverallStatus,
)
from app.db.session import async_session_factory
from app.modules.transcripts.repository import TranscriptRepository
from app.modules.videos.repository import VideoRepository
from app.workers.video_pipeline import VideoPipelineWorker


async def _create_test_video_with_pipeline() -> tuple[Video, Lesson]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        user = User(
            id=uuid4(),
            full_name="Worker Pipeline Test",
            email=f"worker_pipe_{suffix}@example.com",
            password_hash="fakehash",
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.flush()

        cat = Category(name=f"Pipe Cat {suffix}", slug=f"pipe-cat-{suffix}")
        session.add(cat)
        await session.flush()

        course = Course(
            title=f"Pipe Course {suffix}",
            category_id=cat.id,
            price=0,
            status=CourseStatus.DRAFT,
            created_by=user.id,
        )
        session.add(course)
        await session.flush()

        chapter = Chapter(
            title=f"Pipe Chapter {suffix}",
            course_id=course.id,
            order_index=1,
        )
        session.add(chapter)
        await session.flush()

        lesson = Lesson(
            title=f"Pipe Lesson {suffix}",
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
            original_filename="sample_video.mp4",
            file_size_bytes=2 * 1024 * 1024,
            mime_type="video/mp4",
            overall_status=VideoOverallStatus.PROCESSING,
        )
        session.add(video)
        await session.flush()

        repo = VideoRepository(session)
        # Create pipeline steps: upload, transcode, transcribe, index
        steps = [
            PipelineStepRecord(
                id=uuid4(),
                video_id=video.id,
                step=PipelineStep.UPLOAD,
                status=StepStatus.COMPLETED,
                progress=100.0,
            ),
            PipelineStepRecord(
                id=uuid4(),
                video_id=video.id,
                step=PipelineStep.TRANSCODE,
                status=StepStatus.COMPLETED,
                progress=100.0,
            ),
            PipelineStepRecord(
                id=uuid4(),
                video_id=video.id,
                step=PipelineStep.TRANSCRIBE,
                status=StepStatus.PENDING,
                progress=0.0,
            ),
            PipelineStepRecord(
                id=uuid4(),
                video_id=video.id,
                step=PipelineStep.INDEX,
                status=StepStatus.PENDING,
                progress=0.0,
            ),
        ]
        session.add_all(steps)
        await session.commit()
        return video, lesson


@pytest.mark.asyncio
async def test_transcribe_step_execution_and_cleanup() -> None:
    """Spec 11 §4.2, §5.2: Transcribe step extracts WAV, transcribes, persists, cleans files, and advances pipeline."""
    video, lesson = await _create_test_video_with_pipeline()

    # Mock storage and whisper
    mock_storage = MagicMock(spec=S3StorageAdapter)
    mock_ffmpeg = MagicMock(spec=FFmpegAdapter)
    mock_whisper = MagicMock(spec=WhisperAdapter)

    # Fake audio extraction creating an empty file
    def fake_extract(input_p: Path, output_p: Path) -> Path:
        output_p.write_bytes(b"RIFFdummywav")
        return output_p

    mock_ffmpeg.extract_audio_for_whisper.side_effect = fake_extract

    # Fake download creating a dummy file
    def fake_download(key: str, dest_p: Path) -> None:
        dest_p.write_bytes(b"dummyvideo")

    mock_storage.download_file.side_effect = fake_download

    # Fake transcription results
    mock_whisper.transcribe.return_value = [
        WhisperSegmentResult(segment_index=0, start_time=0.0, end_time=3.5, text="Đoạn video mở đầu"),
        WhisperSegmentResult(segment_index=1, start_time=3.5, end_time=7.2, text="Giải thích khái niệm"),
    ]

    worker = VideoPipelineWorker(
        storage=mock_storage,
        ffmpeg=mock_ffmpeg,
        whisper=mock_whisper,
    )

    # Execute one job cycle for this specific video
    processed = await worker._process_next_job(video_id=video.id)
    assert processed is True

    # 1. Verify storage download & ffmpeg audio extraction were called
    mock_storage.download_file.assert_called_once()
    mock_ffmpeg.extract_audio_for_whisper.assert_called_once()
    mock_whisper.transcribe.assert_called_once()

    # 2. Verify temporary files were cleaned up in finally block (Spec 11 §4.2)
    transcribe_dir = worker.work_dir / str(video.id) / "transcribe"
    assert not transcribe_dir.exists()

    # 3. Verify step status updated to COMPLETED and next step INDEX unlocked
    async with async_session_factory() as session:
        repo = VideoRepository(session)
        steps = await repo.get_pipeline_steps(video.id)
        step_dict = {s.step: s for s in steps}

    assert step_dict[PipelineStep.TRANSCRIBE].status == StepStatus.COMPLETED
    assert step_dict[PipelineStep.TRANSCRIBE].progress == 100.0
    # Next step (INDEX) was unlocked (next_attempt_at is None)
    assert step_dict[PipelineStep.INDEX].status == StepStatus.PENDING
    assert step_dict[PipelineStep.INDEX].next_attempt_at is None

    # 4. Verify Transcript and Segments in database
    async with async_session_factory() as session:
        t_repo = TranscriptRepository(session)
        saved_t = await t_repo.get_by_lesson_id(lesson.id)
        assert saved_t is not None
        segments = await t_repo.get_segments_by_transcript_id(saved_t.id)

    assert len(segments) == 2
    assert segments[0].text == "Đoạn video mở đầu"
    assert segments[1].text == "Giải thích khái niệm"


@pytest.mark.asyncio
async def test_transcode_success_unlocks_transcribe() -> None:
    """Spec 11 §11: When TRANSCODE finishes, TRANSCRIBE is unlocked automatically."""
    video, lesson = await _create_test_video_with_pipeline()

    async with async_session_factory() as session:
        repo = VideoRepository(session)
        unlocked = await repo.unlock_next_pipeline_step(video.id, PipelineStep.TRANSCODE)
        await session.commit()

    assert unlocked is not None
    assert unlocked.step == PipelineStep.TRANSCRIBE
    assert unlocked.status == StepStatus.PENDING
    assert unlocked.next_attempt_at is None
