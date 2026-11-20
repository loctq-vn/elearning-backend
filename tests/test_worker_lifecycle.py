"""Tests for Video Worker Lifecycle & Idempotency (Phase C3, Spec 10 §8.2.1, Spec 11 §4, §11)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.adapters.ffmpeg import FFmpegAdapter
from app.db.models.schema import (
    Category,
    Chapter,
    Course,
    CourseStatus,
    Lesson,
    PipelineStep,
    PipelineStepRecord,
    StepStatus,
    User,
    UserRole,
    Video,
    VideoOverallStatus,
)
from app.db.session import async_session_factory
from app.modules.videos.repository import VideoRepository


async def _create_test_hierarchy() -> tuple[Video, PipelineStepRecord]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        user = User(
            id=uuid4(),
            full_name="Worker Test User",
            email=f"worker_test_{suffix}@example.com",
            password_hash="fakehash",
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.flush()

        cat = Category(name=f"Cat {suffix}", slug=f"cat-{suffix}")
        session.add(cat)
        await session.flush()

        course = Course(
            title=f"Course {suffix}",
            category_id=cat.id,
            price=0,
            status=CourseStatus.DRAFT,
            created_by=user.id,
        )
        session.add(course)
        await session.flush()

        chapter = Chapter(course_id=course.id, title="Ch 1", order_index=1)
        session.add(chapter)
        await session.flush()

        lesson = Lesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title="Lesson 1",
            order_index=1,
        )
        session.add(lesson)
        await session.flush()

        video = Video(
            id=uuid4(),
            lesson_id=lesson.id,
            original_filename="test.mp4",
            file_size_bytes=5000000,
            mime_type="video/mp4",
            overall_status=VideoOverallStatus.UPLOADED,
        )
        session.add(video)
        await session.flush()

        step = PipelineStepRecord(
            id=uuid4(),
            video_id=video.id,
            step=PipelineStep.TRANSCRIBE,
            status=StepStatus.PENDING,
            progress=0.0,
            attempt_count=0,
        )
        session.add(step)
        await session.commit()
        return video, step


@pytest.mark.asyncio
async def test_worker_claim_and_lock() -> None:
    video, step = await _create_test_hierarchy()

    async with async_session_factory() as session:
        repo = VideoRepository(session)
        claimed = await repo.claim_next_pending_step(video_id=video.id)
        await session.commit()

    assert claimed is not None
    assert claimed.id == step.id
    assert claimed.status == StepStatus.PROCESSING
    assert claimed.attempt_count == 1
    assert claimed.started_at is not None
    assert claimed.lease_expires_at is not None

    # Calling again for the same video should return None (no other pending steps)
    async with async_session_factory() as session:
        repo = VideoRepository(session)
        second_claim = await repo.claim_next_pending_step(video_id=video.id)
        await session.commit()

    assert second_claim is None


@pytest.mark.asyncio
async def test_worker_heartbeat_lease_renewal() -> None:
    video, step = await _create_test_hierarchy()
    initial_lease = datetime.now(timezone.utc) + timedelta(minutes=30)

    # Set to PROCESSING so worker does not claim it
    async with async_session_factory() as session:
        s_rec = await session.get(PipelineStepRecord, step.id)
        s_rec.status = StepStatus.PROCESSING
        s_rec.lease_expires_at = initial_lease
        await session.commit()

    async with async_session_factory() as session:
        repo = VideoRepository(session)
        renewed = await repo.renew_step_lease(step.id, lease_duration=timedelta(minutes=45))
        await session.commit()

    assert renewed is True

    async with async_session_factory() as session:
        repo = VideoRepository(session)
        updated_step = (await repo.get_pipeline_steps(step.video_id))[0]
        assert updated_step.lease_expires_at > initial_lease


@pytest.mark.asyncio
async def test_orphan_sweep_reclaims_expired_job() -> None:
    video, step = await _create_test_hierarchy()
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Put step in PROCESSING with expired lease
    async with async_session_factory() as session:
        s_rec = await session.get(PipelineStepRecord, step.id)
        s_rec.status = StepStatus.PROCESSING
        s_rec.attempt_count = 1
        s_rec.lease_expires_at = past_time
        await session.commit()

    async with async_session_factory() as session:
        repo = VideoRepository(session)
        reclaimed_count = await repo.sweep_orphaned_jobs(max_attempts=3)
        await session.commit()

    assert reclaimed_count >= 1

    async with async_session_factory() as session:
        s_rec = await session.get(PipelineStepRecord, step.id)
        # Should be rescheduled to PENDING with next_attempt_at
        assert s_rec.status == StepStatus.PENDING
        assert s_rec.next_attempt_at is not None
        assert s_rec.lease_expires_at is None


@pytest.mark.asyncio
async def test_orphan_sweep_marks_failed_after_max_attempts() -> None:
    video, step = await _create_test_hierarchy()
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Put step in PROCESSING at max attempts (3) with expired lease
    async with async_session_factory() as session:
        s_rec = await session.get(PipelineStepRecord, step.id)
        s_rec.status = StepStatus.PROCESSING
        s_rec.attempt_count = 3
        s_rec.lease_expires_at = past_time
        await session.commit()

    async with async_session_factory() as session:
        repo = VideoRepository(session)
        reclaimed_count = await repo.sweep_orphaned_jobs(max_attempts=3)
        await session.commit()

    assert reclaimed_count >= 1

    async with async_session_factory() as session:
        s_rec = await session.get(PipelineStepRecord, step.id)
        assert s_rec.status == StepStatus.FAILED
        assert "timed out" in s_rec.error_message


def test_ffmpeg_probe_and_adapter_installation() -> None:
    adapter = FFmpegAdapter()
    is_installed = adapter.check_installed()
    assert is_installed is True, "FFmpeg and ffprobe must be installed on the system"
