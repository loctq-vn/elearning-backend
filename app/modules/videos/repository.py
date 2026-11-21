"""Video and pipeline data access layer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import (
    Lesson,
    PipelineStep,
    PipelineStepRecord,
    StepStatus,
    Video,
    VideoOverallStatus,
)
from app.modules.videos.schemas import PipelineStepDetail, VideoPipelineStatusResponse

STEP_ORDER = [
    PipelineStep.UPLOAD,
    PipelineStep.TRANSCODE,
    PipelineStep.TRANSCRIBE,
    PipelineStep.INDEX,
]


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
            # Non-upload steps must not be scheduled until upload completes
            step_next_attempt = (
                None if step_enum == PipelineStep.UPLOAD else (now + timedelta(days=365))
            )
            if step_enum in existing_step_map:
                record = existing_step_map[step_enum]
                record.status = StepStatus.PENDING
                record.progress = 0.0
                record.error_message = None
                record.started_at = None
                record.completed_at = None
                record.attempt_count = 0
                record.next_attempt_at = step_next_attempt
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
                    next_attempt_at=step_next_attempt,
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
            elif step.step == PipelineStep.TRANSCODE:
                step.status = StepStatus.PENDING
                step.next_attempt_at = None
                step.updated_at = now

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

    async def get_pipeline_status(self, video_id: UUID) -> VideoPipelineStatusResponse | None:
        """Fetch complete pipeline status for a video including all step records."""
        stmt = (
            select(Video, Lesson.title)
            .join(Lesson, Video.lesson_id == Lesson.id)
            .where(Video.id == video_id)
        )
        row = (await self.db.execute(stmt)).first()
        if not row:
            return None

        video, lesson_title = row
        steps = await self.get_pipeline_steps(video.id)
        step_map = {s.step: s for s in steps}

        step_details: list[PipelineStepDetail] = []
        for step_type in STEP_ORDER:
            s_rec = step_map.get(step_type)
            if s_rec:
                step_details.append(
                    PipelineStepDetail(
                        step=s_rec.step.value,
                        status=s_rec.status.value,
                        progress=s_rec.progress,
                        error_message=s_rec.error_message,
                        started_at=s_rec.started_at,
                        completed_at=s_rec.completed_at,
                    )
                )

        return VideoPipelineStatusResponse(
            video_id=video.id,
            lesson_id=video.lesson_id,
            lesson_title=lesson_title or "",
            steps=step_details,
            overall_status=video.overall_status.value,
            error_message=video.error_message,
            started_at=video.started_at,
            completed_at=video.completed_at,
        )

    async def list_pipeline_statuses(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status_filter: VideoOverallStatus | None = None,
    ) -> tuple[list[VideoPipelineStatusResponse], int]:
        """Fetch paginated video pipeline records."""
        count_stmt = select(func.count(Video.id))
        if status_filter:
            count_stmt = count_stmt.where(Video.overall_status == status_filter)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        query = (
            select(Video, Lesson.title)
            .join(Lesson, Video.lesson_id == Lesson.id)
            .order_by(Video.created_at.desc())
        )
        if status_filter:
            query = query.where(Video.overall_status == status_filter)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        rows = (await self.db.execute(query)).all()

        results: list[VideoPipelineStatusResponse] = []
        for video, lesson_title in rows:
            steps = await self.get_pipeline_steps(video.id)
            step_map = {s.step: s for s in steps}

            step_details: list[PipelineStepDetail] = []
            for step_type in STEP_ORDER:
                s_rec = step_map.get(step_type)
                if s_rec:
                    step_details.append(
                        PipelineStepDetail(
                            step=s_rec.step.value,
                            status=s_rec.status.value,
                            progress=s_rec.progress,
                            error_message=s_rec.error_message,
                            started_at=s_rec.started_at,
                            completed_at=s_rec.completed_at,
                        )
                    )

            results.append(
                VideoPipelineStatusResponse(
                    video_id=video.id,
                    lesson_id=video.lesson_id,
                    lesson_title=lesson_title or "",
                    steps=step_details,
                    overall_status=video.overall_status.value,
                    error_message=video.error_message,
                    started_at=video.started_at,
                    completed_at=video.completed_at,
                )
            )

        return results, total

    async def retry_pipeline_step(
        self,
        video_id: UUID,
        step_enum: PipelineStep,
    ) -> Video:
        """Reset a specific pipeline step to pending and update overall video status."""
        video = await self.get_video_by_id(video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        now = datetime.now(timezone.utc)
        steps = await self.get_pipeline_steps(video_id)
        target_step = next((s for s in steps if s.step == step_enum), None)

        if not target_step:
            raise ValueError(f"Step {step_enum} not found for video {video_id}")

        target_step.status = StepStatus.PENDING
        target_step.progress = 0.0
        target_step.error_message = None
        target_step.started_at = None
        target_step.completed_at = None
        target_step.attempt_count = 0
        target_step.next_attempt_at = None
        target_step.lease_expires_at = None
        target_step.updated_at = now

        # If retrying upload, reset overall to uploading; otherwise processing
        if step_enum == PipelineStep.UPLOAD:
            video.overall_status = VideoOverallStatus.UPLOADING
        else:
            video.overall_status = VideoOverallStatus.PROCESSING
        video.error_message = None
        video.updated_at = now

        await self.db.flush()
        return video

    async def claim_next_pending_step(
        self,
        video_id: UUID | None = None,
        allowed_steps: list[PipelineStep] | None = None,
    ) -> PipelineStepRecord | None:
        """Atomically claim the next eligible pending pipeline step using FOR UPDATE SKIP LOCKED."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(PipelineStepRecord)
            .join(Video, PipelineStepRecord.video_id == Video.id)
            .where(
                Video.overall_status != VideoOverallStatus.UPLOADING,
                PipelineStepRecord.status == StepStatus.PENDING,
                or_(
                    PipelineStepRecord.next_attempt_at.is_(None),
                    PipelineStepRecord.next_attempt_at <= now,
                ),
            )
        )
        if video_id is not None:
            stmt = stmt.where(PipelineStepRecord.video_id == video_id)
        if allowed_steps:
            stmt = stmt.where(PipelineStepRecord.step.in_(allowed_steps))

        stmt = (
            stmt.order_by(PipelineStepRecord.created_at.asc())
            .with_for_update(of=PipelineStepRecord, skip_locked=True)
            .limit(1)
        )
        step_record = (await self.db.execute(stmt)).scalar_one_or_none()
        if not step_record:
            return None

        step_record.status = StepStatus.PROCESSING
        step_record.attempt_count += 1
        step_record.started_at = now
        step_record.lease_expires_at = now + timedelta(minutes=30)
        step_record.updated_at = now

        video = await self.get_video_by_id(step_record.video_id)
        if video and video.overall_status not in (
            VideoOverallStatus.PROCESSING,
            VideoOverallStatus.FAILED,
        ):
            video.overall_status = VideoOverallStatus.PROCESSING
            video.updated_at = now

        await self.db.flush()
        return step_record

    async def renew_step_lease(
        self,
        step_id: UUID,
        lease_duration: timedelta = timedelta(minutes=30),
    ) -> bool:
        """Extend the lease expiration timestamp (heartbeat)."""
        now = datetime.now(timezone.utc)
        stmt = select(PipelineStepRecord).where(
            PipelineStepRecord.id == step_id,
            PipelineStepRecord.status == StepStatus.PROCESSING,
        )
        step = (await self.db.execute(stmt)).scalar_one_or_none()
        if step:
            step.lease_expires_at = now + lease_duration
            step.updated_at = now
            await self.db.flush()
            return True
        return False

    async def update_step_progress(self, step_id: UUID, progress: float) -> None:
        """Update step progress percentage."""
        stmt = select(PipelineStepRecord).where(PipelineStepRecord.id == step_id)
        step = (await self.db.execute(stmt)).scalar_one_or_none()
        if step:
            step.progress = progress
            step.updated_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def mark_step_success(self, step_id: UUID) -> None:
        """Mark a pipeline step as completed."""
        now = datetime.now(timezone.utc)
        stmt = select(PipelineStepRecord).where(PipelineStepRecord.id == step_id)
        step = (await self.db.execute(stmt)).scalar_one_or_none()
        if step:
            step.status = StepStatus.COMPLETED
            step.progress = 100.0
            step.completed_at = now
            step.lease_expires_at = None
            step.error_message = None
            step.updated_at = now
            await self.db.flush()

    async def unlock_next_pipeline_step(
        self,
        video_id: UUID,
        current_step: PipelineStep,
    ) -> PipelineStepRecord | None:
        """Advance the pipeline: transition the subsequent step to PENDING with immediate availability (Spec 11 §11.1)."""
        next_step_map = {
            PipelineStep.UPLOAD: PipelineStep.TRANSCODE,
            PipelineStep.TRANSCODE: PipelineStep.TRANSCRIBE,
            PipelineStep.TRANSCRIBE: PipelineStep.INDEX,
        }
        target_step = next_step_map.get(current_step)
        if not target_step:
            return None

        now = datetime.now(timezone.utc)
        stmt = select(PipelineStepRecord).where(
            PipelineStepRecord.video_id == video_id,
            PipelineStepRecord.step == target_step,
        )
        step = (await self.db.execute(stmt)).scalar_one_or_none()
        if step and step.status == StepStatus.PENDING:
            step.next_attempt_at = None
            step.updated_at = now
            await self.db.flush()
            return step
        return None

    async def mark_step_failure(
        self,
        step_id: UUID,
        error_msg: str,
        backoff_seconds: int | None = None,
    ) -> None:
        """Mark a pipeline step as failed or schedule retry with backoff."""
        now = datetime.now(timezone.utc)
        stmt = select(PipelineStepRecord).where(PipelineStepRecord.id == step_id)
        step = (await self.db.execute(stmt)).scalar_one_or_none()
        if not step:
            return

        step.error_message = error_msg
        step.lease_expires_at = None
        step.updated_at = now

        if backoff_seconds is not None:
            # Requeue for retry
            step.status = StepStatus.PENDING
            step.next_attempt_at = now + timedelta(seconds=backoff_seconds)
        else:
            # Final failure after 3 attempts
            step.status = StepStatus.FAILED
            video = await self.get_video_by_id(step.video_id)
            if video:
                video.overall_status = VideoOverallStatus.FAILED
                video.error_message = f"Bước {step.step.value} thất bại: {error_msg}"
                video.updated_at = now

        await self.db.flush()

    async def sweep_orphaned_jobs(self, max_attempts: int = 3) -> int:
        """Reclaim jobs left in PROCESSING past lease expiration."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(PipelineStepRecord)
            .where(
                PipelineStepRecord.status == StepStatus.PROCESSING,
                PipelineStepRecord.lease_expires_at < now,
            )
            .with_for_update(skip_locked=True)
        )
        orphans = list((await self.db.execute(stmt)).scalars().all())
        reclaimed = 0

        # Backoff intervals per Spec 11 §11.1: 30s, 120s, 600s
        backoffs = [30, 120, 600]

        for job in orphans:
            reclaimed += 1
            if job.attempt_count < max_attempts:
                idx = min(job.attempt_count - 1, len(backoffs) - 1)
                delay = backoffs[idx] if idx >= 0 else 30
                job.status = StepStatus.PENDING
                job.next_attempt_at = now + timedelta(seconds=delay)
                job.error_message = f"Job hết hạn lease (worker timed out), lên lịch thử lại lần {job.attempt_count + 1}."
            else:
                job.status = StepStatus.FAILED
                job.error_message = "Job hết hạn lease sau số lần thử tối đa (worker timed out)."
                video = await self.get_video_by_id(job.video_id)
                if video:
                    video.overall_status = VideoOverallStatus.FAILED
                    video.error_message = job.error_message
                    video.updated_at = now
            job.lease_expires_at = None
            job.updated_at = now

        if reclaimed:
            await self.db.flush()
        return reclaimed
