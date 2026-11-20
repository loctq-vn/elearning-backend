"""Video transcoding, transcription, embedding, and indexing worker (Spec 10 §8.2, Spec 11 §4, §11)."""

from __future__ import annotations

import asyncio
import logging
import shutil
import signal
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.adapters.ffmpeg import FFmpegAdapter
from app.adapters.storage import (
    S3StorageAdapter,
    video_hls_master_key,
    video_raw_key,
)
from app.core.config import Settings, settings
from app.db.models.schema import (
    PipelineStep,
    StepStatus,
    VideoOverallStatus,
)
from app.db.session import async_session_factory
from app.modules.videos.repository import VideoRepository

logger = logging.getLogger("worker.video_pipeline")

# Backoff intervals per Spec 11 §11.1: 30s, 2m (120s), 10m (600s)
BACKOFF_INTERVALS = [30, 120, 600]
MAX_ATTEMPTS = 3
POLL_INTERVAL_SECONDS = 5.0
SWEEP_INTERVAL_SECONDS = 60.0


class VideoPipelineWorker:
    """Background worker processing video pipeline steps asynchronously."""

    def __init__(
        self,
        config: Settings = settings,
        storage: S3StorageAdapter | None = None,
        ffmpeg: FFmpegAdapter | None = None,
    ) -> None:
        self.config = config
        self.storage = storage or S3StorageAdapter(config)
        self.ffmpeg = ffmpeg or FFmpegAdapter()
        self.work_dir = Path(tempfile.gettempdir()) / "elearning_worker"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        """Signal the worker loop to terminate gracefully."""
        logger.info("Stopping video pipeline worker...")
        self._stop_event.set()

    async def run(self) -> None:
        """Main worker loop polling for pending jobs and sweeping orphans."""
        logger.info(
            "Video pipeline worker started. Polling every %s seconds.", POLL_INTERVAL_SECONDS
        )
        last_sweep = 0.0

        while not self._stop_event.is_set():
            loop_now = asyncio.get_running_loop().time()

            # 1. Sweep orphaned jobs periodically
            if loop_now - last_sweep >= SWEEP_INTERVAL_SECONDS:
                try:
                    await self._sweep_orphans()
                except Exception as exc:
                    logger.error("Error during orphan sweep: %s", exc)
                last_sweep = loop_now

            # 2. Claim and process next available job
            job_processed = False
            try:
                job_processed = await self._process_next_job()
            except Exception as exc:
                logger.error("Unhandled error processing job: %s\n%s", exc, traceback.format_exc())

            # 3. If no job was ready, wait before next poll
            if not job_processed and not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)
                except asyncio.TimeoutError:
                    pass

        logger.info("Video pipeline worker stopped cleanly.")

    async def _sweep_orphans(self) -> None:
        """Find and recover jobs with expired leases."""
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            reclaimed = await repo.sweep_orphaned_jobs(max_attempts=MAX_ATTEMPTS)
            if reclaimed > 0:
                await session.commit()
                logger.warning("Reclaimed %d orphaned/expired pipeline jobs.", reclaimed)

    async def _process_next_job(self) -> bool:
        """Claim a single pending job and execute it."""
        claimed_job_id: UUID | None = None
        step_type: PipelineStep | None = None

        # 1. Atomic claim via FOR UPDATE SKIP LOCKED (Phase C worker handles transcoding)
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            step_record = await repo.claim_next_pending_step(allowed_steps=[PipelineStep.TRANSCODE])
            if not step_record:
                return False

            claimed_job_id = step_record.id
            step_type = step_record.step
            attempt_count = step_record.attempt_count
            video_id = step_record.video_id
            await session.commit()

        logger.info(
            "Claimed job %s: step=%s, video=%s, attempt=%d",
            claimed_job_id,
            step_type.value,
            video_id,
            attempt_count,
        )

        # 2. Execute the claimed step
        job_done_event = asyncio.Event()
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(claimed_job_id, job_done_event))

        try:
            if step_type == PipelineStep.TRANSCODE:
                await self._handle_transcode_step(claimed_job_id, video_id)
                # Mark step completed
                async with async_session_factory() as session:
                    repo = VideoRepository(session)
                    await repo.mark_step_success(claimed_job_id)
                    # Check overall video completion
                    await self._check_video_completion(repo, video_id)
                    await session.commit()
                logger.info(
                    "Successfully completed job %s (step=%s)", claimed_job_id, step_type.value
                )
            else:
                logger.info("Step %s is not handled by video pipeline worker.", step_type.value)

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc!s}"
            logger.error("Job %s failed: %s\n%s", claimed_job_id, error_msg, traceback.format_exc())

            # Determine retry or final failure
            async with async_session_factory() as session:
                repo = VideoRepository(session)
                if attempt_count < MAX_ATTEMPTS:
                    idx = min(attempt_count - 1, len(BACKOFF_INTERVALS) - 1)
                    backoff = BACKOFF_INTERVALS[idx]
                    logger.info(
                        "Scheduling retry %d for job %s in %d seconds.",
                        attempt_count + 1,
                        claimed_job_id,
                        backoff,
                    )
                    await repo.mark_step_failure(claimed_job_id, error_msg, backoff_seconds=backoff)
                else:
                    logger.error(
                        "Job %s reached max attempts (%d). Marking as permanently FAILED.",
                        claimed_job_id,
                        MAX_ATTEMPTS,
                    )
                    await repo.mark_step_failure(claimed_job_id, error_msg, backoff_seconds=None)
                await session.commit()

        finally:
            job_done_event.set()
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        return True

    async def _heartbeat_loop(self, step_id: UUID, done_event: asyncio.Event) -> None:
        """Renew lease every 30 seconds while processing."""
        while not done_event.is_set():
            try:
                await asyncio.wait_for(done_event.wait(), timeout=30.0)
                break
            except asyncio.TimeoutError:
                pass

            if not done_event.is_set():
                try:
                    async with async_session_factory() as session:
                        repo = VideoRepository(session)
                        renewed = await repo.renew_step_lease(step_id)
                        if renewed:
                            await session.commit()
                            logger.debug("Renewed heartbeat lease for step %s", step_id)
                except Exception as exc:
                    logger.warning("Heartbeat lease renewal failed for step %s: %s", step_id, exc)

    async def _handle_transcode_step(self, step_id: UUID, video_id: UUID) -> None:
        """Transcode video to 1080p, 720p, 480p HLS and upload to S3 (Spec 11 §4.1)."""
        video_dir = self.work_dir / str(video_id)
        hls_dir = video_dir / "hls"
        if video_dir.exists():
            shutil.rmtree(video_dir, ignore_errors=True)
        video_dir.mkdir(parents=True, exist_ok=True)
        hls_dir.mkdir(parents=True, exist_ok=True)

        async with async_session_factory() as session:
            repo = VideoRepository(session)
            video = await repo.get_video_by_id(video_id)
            if not video:
                raise ValueError(f"Video {video_id} does not exist")
            filename = video.original_filename

        raw_key = video_raw_key(str(video_id), filename)
        local_raw_path = video_dir / filename

        # 1. Idempotency cleanup: delete any existing HLS segments on S3
        s3_hls_prefix = f"hls/{video_id}"
        deleted_count = self.storage.delete_prefix(s3_hls_prefix)
        logger.info(
            "Idempotency: cleaned %d existing S3 objects under '%s'", deleted_count, s3_hls_prefix
        )

        # 2. Download raw video from S3
        logger.info("Downloading raw video from S3: '%s' -> '%s'", raw_key, local_raw_path)
        self.storage.download_file(raw_key, local_raw_path)

        # 3. Probe video metadata
        probe_info = self.ffmpeg.probe(local_raw_path)
        logger.info(
            "Video probed: duration=%.2fs, resolution=%dx%d, fps=%.2f",
            probe_info.duration_seconds,
            probe_info.width,
            probe_info.height,
            probe_info.fps,
        )

        # Update duration on video record
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            v = await repo.get_video_by_id(video_id)
            if v:
                v.duration_seconds = probe_info.duration_seconds
                v.updated_at = datetime.now(timezone.utc)
                await session.commit()

        # 4. Transcode to HLS with progress tracking
        def on_transcode_progress(percent: float) -> None:
            # We schedule progress update asynchronously or log it
            logger.info("Transcode progress for video %s: %.1f%%", video_id, percent)

        logger.info("Starting HLS multi-rendition transcoding for video %s...", video_id)
        generated_files = self.ffmpeg.transcode_to_hls(
            input_path=local_raw_path,
            output_dir=hls_dir,
            probe_info=probe_info,
            progress_callback=on_transcode_progress,
        )
        logger.info("Transcode generated %d files in %s", len(generated_files), hls_dir)

        # 5. Extract audio WAV (mono 16kHz) for Whisper (Phase D1 prep)
        audio_wav_path = video_dir / "audio_16k.wav"
        try:
            self.ffmpeg.extract_audio_for_whisper(local_raw_path, audio_wav_path)
            logger.info("Extracted audio for Whisper: %s", audio_wav_path)
        except Exception as exc:
            logger.warning("Audio extraction notice (non-fatal for HLS): %s", exc)

        # 6. Upload all HLS files to S3 under hls/{video_id}/
        logger.info(
            "Uploading %d HLS files to S3 prefix '%s'...", len(generated_files), s3_hls_prefix
        )
        uploaded_keys = self.storage.upload_directory(hls_dir, s3_hls_prefix)
        logger.info("Successfully uploaded %d HLS files to S3.", len(uploaded_keys))

        # 7. Update video.hls_master_url
        master_url = self.storage.public_url(video_hls_master_key(str(video_id)))
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            v = await repo.get_video_by_id(video_id)
            if v:
                v.hls_master_url = master_url
                v.updated_at = datetime.now(timezone.utc)
                await session.commit()
        logger.info("Updated video %s hls_master_url: %s", video_id, master_url)

        # 8. Clean up local temporary files
        shutil.rmtree(video_dir, ignore_errors=True)

    async def _check_video_completion(self, repo: VideoRepository, video_id: UUID) -> None:
        """Update overall video status to COMPLETED if all pipeline steps are COMPLETED."""
        steps = await repo.get_pipeline_steps(video_id)
        all_completed = len(steps) > 0 and all(s.status == StepStatus.COMPLETED for s in steps)
        if all_completed:
            video = await repo.get_video_by_id(video_id)
            if video:
                now = datetime.now(timezone.utc)
                video.overall_status = VideoOverallStatus.COMPLETED
                video.completed_at = now
                video.updated_at = now
                await repo.db.flush()
                logger.info(
                    "All pipeline steps completed for video %s! Overall status -> COMPLETED",
                    video_id,
                )


async def main() -> None:
    """Worker entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    worker = VideoPipelineWorker()

    loop = asyncio.get_running_loop()

    def handle_signal() -> None:
        logger.info("Received termination signal.")
        worker.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except (NotImplementedError, AttributeError):
            # Windows signal handling fallback
            pass

    try:
        await worker.run()
    except (KeyboardInterrupt, SystemExit):
        worker.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
