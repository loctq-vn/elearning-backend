"""End-to-End Verification Script for Video Pipeline & CloudFront Delivery (C3.04 - C3.07).

Flow:
1. Initialize test curriculum and admin user in DB.
2. Direct S3 multipart upload with real video 'media/short video.mp4'.
3. Complete upload to trigger pipeline.
4. Execute worker transcode to generate multi-rendition HLS (1080p, 720p, 480p) + 16kHz audio.
5. Upload HLS files to S3 prefix hls/{video_id}/.
6. Verify CloudFront delivery of master.m3u8, rendition playlists, and .ts segments.
7. Verify Admin pipeline control APIs (Status, List, Retry, Cancel - Contract 08 §9.2 - §9.5).
8. Verify Student lesson player endpoint (Contract 08 §2.7).
"""

from __future__ import annotations

import asyncio
import re
import sys
import urllib.request
from pathlib import Path
from uuid import uuid4

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from app.adapters.ffmpeg import FFmpegAdapter
from app.adapters.storage import S3StorageAdapter, video_hls_master_key
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.models.schema import (
    Category,
    Chapter,
    Course,
    CourseStatus,
    Lesson,
    PipelineStep,
    StepStatus,
    User,
    UserRole,
    Video,
    VideoOverallStatus,
)
from app.db.session import async_session_factory
from app.main import app
from app.modules.videos.repository import VideoRepository
from app.workers.video_pipeline import VideoPipelineWorker


async def setup_test_data() -> tuple[User, str, Category, Course, Chapter, Lesson]:
    """Create test category, course, chapter, lesson, and admin user."""
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        admin = User(
            id=uuid4(),
            full_name=f"E2E Admin C3 {suffix}",
            email=f"admin_c3_{suffix}@example.com",
            password_hash=get_password_hash("AdminPass@123"),
            role=UserRole.ADMIN,
            is_verified=True,
            is_locked=False,
        )
        session.add(admin)
        await session.flush()

        token = create_access_token(admin.id)

        category = Category(
            name=f"C3 Test Cat {suffix}",
            slug=f"c3-cat-{suffix}",
        )
        session.add(category)
        await session.flush()

        course = Course(
            title=f"C3 Test Course {suffix}",
            category_id=category.id,
            price=0,
            status=CourseStatus.PUBLISHED,
            created_by=admin.id,
        )
        session.add(course)
        await session.flush()

        chapter = Chapter(
            course_id=course.id,
            title=f"C3 Chapter {suffix}",
            order_index=1,
        )
        session.add(chapter)
        await session.flush()

        lesson = Lesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title=f"C3 HLS Player Lesson {suffix}",
            order_index=1,
            is_trial_allowed=True,
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(category)
        await session.refresh(course)
        await session.refresh(lesson)

        return admin, token, category, course, chapter, lesson


async def main() -> None:
    print("=" * 70)
    print("STARTING FULL END-TO-END VIDEO PIPELINE & CLOUDFRONT VERIFICATION")
    print(f"Bucket: {settings.s3_bucket_name}")
    print(f"CloudFront: {settings.cloudfront_domain}")
    print("=" * 70)

    # 0. Check real test video file
    video_path = (
        Path("media/short_sample.mp4")
        if Path("media/short_sample.mp4").exists()
        else Path("media/short video.mp4")
    )
    if not video_path.exists():
        raise FileNotFoundError(f"Missing test video at: {video_path}")
    video_bytes = video_path.read_bytes()
    file_size = len(video_bytes)
    print(f"\n[0] Loaded media file: '{video_path.name}' ({file_size / 1024 / 1024:.2f} MB)")

    # 1. Setup entities in DB
    admin, token, category, course, chapter, lesson = await setup_test_data()
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[1] Test DB entities ready: Course '{course.title}', Lesson ID '{lesson.id}'")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # 2. Upload Init (Contract 08 §9.1a)
        print("\n--- STEP 1: Upload Init (POST /api/admin/videos/upload/init) ---")
        init_res = await client.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(lesson.id),
                "file_name": video_path.name,
                "file_size": file_size,
                "content_type": "video/mp4",
            },
            headers=headers,
        )
        assert init_res.status_code == 200, f"Init failed: {init_res.text}"
        init_data = init_res.json()
        video_id = init_data["video_id"]
        upload_id = init_data["upload_id"]
        total_parts = init_data["total_parts"]
        print(f"Upload initiated: video_id={video_id}, upload_id={upload_id}, total_parts={total_parts}")

        # 3. Get Presigned URL (Contract 08 §9.1b)
        print("\n--- STEP 2: Presigned Part URL (POST /api/admin/videos/upload) ---")
        part_url_res = await client.post(
            "/api/admin/videos/upload",
            json={
                "video_id": video_id,
                "upload_id": upload_id,
                "part_number": 1,
            },
            headers=headers,
        )
        assert part_url_res.status_code == 200, f"Get part URL failed: {part_url_res.text}"
        presigned_url = part_url_res.json()["presigned_url"]
        print("Presigned PUT URL generated successfully.")

        # 4. Upload raw video chunk directly to S3
        print("\n--- STEP 3: Client Direct Upload Part 1 to AWS S3 ---")
        async with httpx.AsyncClient(timeout=120.0) as s3_http:
            put_res = await s3_http.put(
                presigned_url,
                content=video_bytes,
                headers={"Content-Type": "video/mp4"},
            )
        assert put_res.status_code == 200, f"S3 PUT failed: {put_res.status_code}"
        etag = put_res.headers.get("ETag", "").strip('"')
        assert etag, "No ETag received from S3"
        print(f"S3 Direct Upload succeeded! ETag={etag}")

        # 5. Complete Upload (Contract 08 §9.1c)
        print("\n--- STEP 4: Complete Upload (POST /api/admin/videos/upload/complete) ---")
        comp_res = await client.post(
            "/api/admin/videos/upload/complete",
            json={
                "video_id": video_id,
                "upload_id": upload_id,
                "parts": [{"part_number": 1, "etag": etag}],
            },
            headers=headers,
        )
        assert comp_res.status_code == 200, f"Complete failed: {comp_res.text}"
        comp_data = comp_res.json()
        print(f"Complete OK: {comp_data['message']}")

        # 6. Check Initial Pipeline Status (Contract 08 §9.2)
        print("\n--- STEP 5: Pipeline Status Polling (GET /api/admin/pipeline/{video_id}/status) ---")
        status_res = await client.get(
            f"/api/admin/pipeline/{video_id}/status",
            headers=headers,
        )
        assert status_res.status_code == 200
        status_data = status_res.json()
        print(f"Current overall_status: {status_data['overall_status']}")
        for s in status_data["steps"]:
            print(f"  Step '{s['step']}': status={s['status']}, progress={s['progress']}")

        # 7. Execute Worker Transcoding (C3.01 - C3.03)
        print("\n--- STEP 6: Worker HLS Multi-Rendition Transcoding ---")
        worker = VideoPipelineWorker()
        from datetime import datetime, timedelta, timezone
        from uuid import UUID
        vid_uuid = UUID(video_id)
        
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            steps = await repo.get_pipeline_steps(vid_uuid)
            transcode_step = next(s for s in steps if s.step == PipelineStep.TRANSCODE)
            # Set to PROCESSING so background workers don't race
            transcode_step.status = StepStatus.PROCESSING
            transcode_step.started_at = datetime.now(timezone.utc)
            transcode_step.lease_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
            await session.commit()
            transcode_step_id = transcode_step.id

        print(f"Running _handle_transcode_step on step ID {transcode_step_id}...")
        await worker._handle_transcode_step(transcode_step_id, vid_uuid)

        # Mark transcode step completed in DB
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            await repo.mark_step_success(transcode_step_id)
            await session.commit()
        print("Worker transcode step executed and marked COMPLETED!")

        # 8. Check Video Record hls_master_url in DB
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            vid_record = await repo.get_video_by_id(vid_uuid)
            assert vid_record is not None
            assert vid_record.hls_master_url is not None
            master_url = vid_record.hls_master_url
            print(f"\n[DB] Video hls_master_url updated: {master_url}")

        # 9. CloudFront HLS Delivery Verification (C3.04)
        print("\n--- STEP 7: Verify CloudFront HLS Delivery (C3.04) ---")
        print(f"Fetching master playlist from CloudFront: {master_url}")
        
        req = urllib.request.Request(master_url, headers={"User-Agent": "Mozilla/5.0 (E2E-Verifier)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            assert resp.status == 200, f"CloudFront returned HTTP {resp.status}"
            master_content = resp.read().decode("utf-8")
        
        print(">>> HTTP 200 OK from CloudFront!")
        print("Master playlist preview:")
        for line in master_content.strip().splitlines()[:10]:
            print("  ", line)

        assert "#EXTM3U" in master_content, "master.m3u8 missing #EXTM3U header"
        assert "RESOLUTION=" in master_content, "master.m3u8 missing variant streams"

        # Find first sub-playlist (e.g. 1080p.m3u8, 720p.m3u8, or 480p.m3u8)
        renditions = [line.strip() for line in master_content.splitlines() if line.strip() and not line.startswith("#")]
        print(f"Found {len(renditions)} HLS renditions in master playlist: {renditions}")
        assert len(renditions) >= 1, "No rendition playlists found in master.m3u8"

        first_rendition = renditions[0]
        base_hls_url = master_url.rsplit("/", 1)[0]
        rendition_url = f"{base_hls_url}/{first_rendition}"
        print(f"\nFetching variant playlist from CloudFront: {rendition_url}")
        req_rendition = urllib.request.Request(rendition_url, headers={"User-Agent": "Mozilla/5.0 (E2E-Verifier)"})
        with urllib.request.urlopen(req_rendition, timeout=30) as resp_r:
            assert resp_r.status == 200
            rendition_content = resp_r.read().decode("utf-8")

        print(">>> Variant playlist HTTP 200 OK!")
        segments = [line.strip() for line in rendition_content.splitlines() if line.strip() and not line.startswith("#")]
        print(f"Total TS segments in variant playlist: {len(segments)}")
        assert len(segments) > 0, "No .ts segments found in variant playlist"

        # Fetch first TS segment via CloudFront
        first_segment = segments[0]
        segment_url = f"{base_hls_url}/{first_segment}"
        print(f"\nFetching sample video segment from CloudFront: {segment_url}")
        req_seg = urllib.request.Request(segment_url, headers={"User-Agent": "Mozilla/5.0 (E2E-Verifier)"})
        with urllib.request.urlopen(req_seg, timeout=30) as resp_s:
            assert resp_s.status == 200
            seg_bytes = resp_s.read()
            content_type = resp_s.headers.get("Content-Type")
            print(f">>> Segment HTTP 200 OK! Size: {len(seg_bytes)} bytes, Content-Type: {content_type}")
            assert len(seg_bytes) > 0

        # 10. Pipeline Control Verification (C3.05)
        print("\n--- STEP 8: Verify Admin Pipeline Control APIs (C3.05) ---")
        headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}
        
        # 10a. Admin List Pipelines (Contract 08 §9.3)
        print("Testing GET /api/admin/pipeline...")
        list_res = await client.get("/api/admin/pipeline?page=1&page_size=10", headers=headers)
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert "data" in list_data
        print(f"List pipelines OK: total={list_data['total']} items")

        # 10b. Pipeline Retry (Contract 08 §9.4)
        print(f"Testing POST /api/admin/pipeline/{video_id}/retry?step=transcode...")
        retry_res = await client.post(
            f"/api/admin/pipeline/{video_id}/retry?step=transcode",
            headers=headers,
        )
        assert retry_res.status_code == 200, f"Retry failed: {retry_res.text}"
        print(f"Retry OK: {retry_res.json()['message']}")

        # Verify step reset to pending in DB
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            steps = await repo.get_pipeline_steps(vid_uuid)
            tc_step = next(s for s in steps if s.step == PipelineStep.TRANSCODE)
            assert tc_step.status == StepStatus.PENDING
            print(f"DB verification: Transcode step status reset to '{tc_step.status.value}'")

        # 10c. Pipeline Cancel (Contract 08 §9.5)
        print(f"Testing PUT /api/admin/pipeline/{video_id}/cancel...")
        cancel_res = await client.put(
            f"/api/admin/pipeline/{video_id}/cancel",
            headers=headers,
        )
        assert cancel_res.status_code == 200, f"Cancel failed: {cancel_res.text}"
        print(f"Cancel OK: {cancel_res.json()['message']}, overall_status={cancel_res.json()['overall_status']}")

        # 11. Student Lesson Player Contract Verification (Contract 08 §2.7)
        print("\n--- STEP 9: Verify Lesson Player Data Contract (Contract 08 §2.7) ---")
        
        # Reset master_url and completed status on video and all steps so worker doesn't re-claim
        async with async_session_factory() as session:
            repo = VideoRepository(session)
            v = await repo.get_video_by_id(vid_uuid)
            if v:
                v.hls_master_url = master_url
                v.overall_status = VideoOverallStatus.COMPLETED
            steps = await repo.get_pipeline_steps(vid_uuid)
            for s in steps:
                s.status = StepStatus.COMPLETED
            await session.commit()

        player_res = await client.get(
            f"/api/lessons/{lesson.id}",
            headers=headers,
        )
        assert player_res.status_code == 200, f"Player API failed: {player_res.text}"
        player_data = player_res.json()
        assert "hls_stream_url" in player_data
        assert player_data["hls_stream_url"] == master_url
        print(f"Player contract verified! hls_stream_url = '{player_data['hls_stream_url']}'")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED: C3.04, C3.05, C3.06, C3.07 VERIFIED SUCCESSFULLY!")
    print(f"CloudFront Master Stream: {master_url}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
