"""Video and pipeline data access layer."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import (
    Lesson,
    PipelineStep,
    PipelineStepRecord,
    StepStatus,
    Video,
    VideoOverallStatus,
)


class VideoRepository:
    """Repository handling video records and pipeline steps."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_lesson(self, lesson_id: UUID) -> Lesson | None:
        """Fetch lesson by ID."""
        stmt = select(Lesson).where(Lesson.id == lesson_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_video_by_id(self, video_id: UUID) -> Video | None:
        """Fetch video by primary key."""
        stmt = select(Video).where(Video.id == video_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_video_by_lesson_id(self, lesson_id: UUID) -> Video | None:
        """Fetch video by lesson FK."""
        stmt = select(Video).where(Video.lesson_id == lesson_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_pipeline_steps(self, video_id: UUID) -> list[PipelineStepRecord]:
        """Fetch all pipeline step records for a video."""
        stmt = select(PipelineStepRecord).where(PipelineStepRecord.video_id == video_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_or_update_video_for_upload(
        self,
        *,
        lesson_id: UUID,
        file_name: str,
        file_size: int,
        content_type: str,
        reuse_video_id: UUID | None = None,
    ) -> Video:
        """Create a new video record or reset existing one for upload initialization."""
        existing_video = await self.get_video_by_lesson_id(lesson_id)
        now = datetime.now(timezone.utc)

        if existing_video is not None:
            video = existing_video
            video.original_filename = file_name
            video.file_size_bytes = file_size
            video.mime_type = content_type
            video.raw_storage_url = None
            video.hls_master_url = None
            video.duration_seconds = None
            video.overall_status = VideoOverallStatus.UPLOADING
            video.error_message = None
            video.started_at = now
            video.completed_at = None
            video.updated_at = now
        else:
            video = Video(
                id=reuse_video_id or uuid4(),
                lesson_id=lesson_id,
                original_filename=file_name,
                file_size_bytes=file_size,
                mime_type=content_type,
                raw_storage_url=None,
                hls_master_url=None,
                duration_seconds=None,
                overall_status=VideoOverallStatus.UPLOADING,
                error_message=None,
                started_at=now,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
            self.db.add(video)

        await self.db.flush()

        # Ensure 4 pipeline step records exist
        existing_steps = await self.get_pipeline_steps(video.id)
        existing_step_map = {step.step: step for step in existing_steps}

        for step_enum in (
            PipelineStep.UPLOAD,
            PipelineStep.TRANSCODE,
            PipelineStep.TRANSCRIBE,
            PipelineStep.INDEX,
        ):
            if step_enum in existing_step_map:
                record = existing_step_map[step_enum]
                record.status = StepStatus.PENDING
                record.progress = 0.0
                record.error_message = None
                record.started_at = None
                record.completed_at = None
                record.attempt_count = 0
                record.next_attempt_at = None
                record.lease_expires_at = None
                record.updated_at = now
            else:
                new_record = PipelineStepRecord(
                    id=uuid4(),
                    video_id=video.id,
                    step=step_enum,
                    status=StepStatus.PENDING,
                    progress=0.0,
                    error_message=None,
                    started_at=None,
                    completed_at=None,
                    attempt_count=0,
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(new_record)

        await self.db.flush()
        return video

    async def mark_upload_completed(
        self,
        *,
        video: Video,
        raw_storage_url: str,
    ) -> Video:
        """Mark video upload as completed and update the upload step."""
        now = datetime.now(timezone.utc)
        video.raw_storage_url = raw_storage_url
        video.overall_status = VideoOverallStatus.UPLOADED
        video.updated_at = now

        existing_steps = await self.get_pipeline_steps(video.id)
        for step in existing_steps:
            if step.step == PipelineStep.UPLOAD:
                step.status = StepStatus.COMPLETED
                step.progress = 100.0
                step.completed_at = now
                step.updated_at = now
                break

        await self.db.flush()
        return video

    async def mark_upload_cancelled(
        self,
        *,
        video: Video,
    ) -> Video:
        """Mark video pipeline/upload as cancelled and revert to uploaded."""
        now = datetime.now(timezone.utc)
        video.overall_status = VideoOverallStatus.UPLOADED
        video.updated_at = now

        await self.db.flush()
        return video
