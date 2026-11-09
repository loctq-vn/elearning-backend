"""End-to-End Real S3 Upload Verification Script (C2.04 / C2.05).

Tests:
1. Small video single-part direct upload to real AWS S3 bucket.
2. Large video multipart direct upload (2 parts) to real AWS S3 bucket.
3. Interrupted upload resume verification against S3 list_parts.
4. Upload cancellation / abort multipart upload on S3.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from app.adapters.storage import S3StorageAdapter
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.models.schema import (
    Category,
    Chapter,
    Course,
    CourseStatus,
    Lesson,
    User,
    UserRole,
)
from app.db.session import async_session_factory
from app.main import app


async def setup_test_entities() -> tuple[str, str, Lesson, Lesson]:
    """Create test admin and 2 lessons for short and long video tests."""
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        admin = User(
            id=uuid4(),
            full_name=f"E2E Admin {suffix}",
            email=f"e2e_admin_{suffix}@example.com",
            password_hash=get_password_hash("AdminPass@123"),
            role=UserRole.ADMIN,
            is_verified=True,
            is_locked=False,
        )
        session.add(admin)
        await session.flush()

        token = create_access_token(admin.id)

        category = Category(
            name=f"E2E Cat {suffix}",
            slug=f"e2e-cat-{suffix}",
        )
        session.add(category)
        await session.flush()

        course = Course(
            title=f"E2E Course {suffix}",
            category_id=category.id,
            price=0,
            status=CourseStatus.DRAFT,
            created_by=admin.id,
        )
        session.add(course)
        await session.flush()

        chapter = Chapter(
            course_id=course.id,
            title=f"E2E Chapter {suffix}",
            order_index=1,
        )
        session.add(chapter)
        await session.flush()

        lesson_short = Lesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title=f"Short Video Lesson {suffix}",
            order_index=1,
            is_trial_allowed=True,
        )
        lesson_long = Lesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title=f"Long Video Lesson {suffix}",
            order_index=2,
            is_trial_allowed=False,
        )
        session.add_all([lesson_short, lesson_long])
        await session.commit()
        await session.refresh(lesson_short)
        await session.refresh(lesson_long)

        return admin.email, token, lesson_short, lesson_long


async def run_e2e_tests() -> None:
    print("=" * 60)
    print("STARTING REAL S3 UPLOAD E2E INTEGRATION TEST (C2.04)")
    print("Bucket:", settings.s3_bucket_name)
    print("=" * 60)

    # Check media files
    short_video_path = Path("media/short video.mp4")
    long_video_path = Path("media/long video.mp4")

    if not short_video_path.exists() or not long_video_path.exists():
        raise FileNotFoundError("Video test files not found in media/")

    short_video_bytes = short_video_path.read_bytes()
    long_video_bytes = long_video_path.read_bytes()
    print(
        f"Short video: {len(short_video_bytes)} bytes ({len(short_video_bytes) / 1024 / 1024:.2f} MB)"
    )
    print(
        f"Long video: {len(long_video_bytes)} bytes ({len(long_video_bytes) / 1024 / 1024:.2f} MB)"
    )

    # Setup DB
    admin_email, token, lesson_short, lesson_long = await setup_test_entities()
    headers = {"Authorization": f"Bearer {token}"}
    storage = S3StorageAdapter(settings)
    s3_client = storage._client()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # ──────────────────────────────────────────────────────────────────────
        # TEST 1: Small Video (1 Part) Direct Upload to Real S3
        # ──────────────────────────────────────────────────────────────────────
        print("\n--- [TEST 1] Small Video Single-Part Upload ---")
        init_res = await client.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(lesson_short.id),
                "file_name": "short video.mp4",
                "file_size": len(short_video_bytes),
                "content_type": "video/mp4",
            },
            headers=headers,
        )
        assert init_res.status_code == 200, f"Init failed: {init_res.text}"
        init_data = init_res.json()
        short_vid_id = init_data["video_id"]
        short_upload_id = init_data["upload_id"]
        print(
            f"Init OK: video_id={short_vid_id}, upload_id={short_upload_id}, total_parts={init_data['total_parts']}"
        )
        assert init_data["total_parts"] == 1

        # Get presigned URL for part 1
        part1_url_res = await client.post(
            "/api/admin/videos/upload",
            json={
                "video_id": short_vid_id,
                "upload_id": short_upload_id,
                "part_number": 1,
            },
            headers=headers,
        )
        assert part1_url_res.status_code == 200, f"Get part URL failed: {part1_url_res.text}"
        presigned_url_1 = part1_url_res.json()["presigned_url"]
        print("Presigned URL received for part 1")

        # Client PUTs chunk directly to AWS S3
        async with httpx.AsyncClient(timeout=60.0) as s3_http_client:
            put_res = await s3_http_client.put(
                presigned_url_1,
                content=short_video_bytes,
                headers={"Content-Type": "video/mp4"},
            )
        assert put_res.status_code == 200, f"S3 PUT failed with status {put_res.status_code}"
        etag_1 = put_res.headers.get("ETag", "").strip('"')
        print(f"S3 PUT part 1 successful! ETag={etag_1}")
        assert etag_1, "Missing ETag in S3 response"

        # Complete upload
        comp_res = await client.post(
            "/api/admin/videos/upload/complete",
            json={
                "video_id": short_vid_id,
                "upload_id": short_upload_id,
                "parts": [{"part_number": 1, "etag": etag_1}],
            },
            headers=headers,
        )
        assert comp_res.status_code == 200, f"Complete failed: {comp_res.text}"
        comp_data = comp_res.json()
        assert comp_data["overall_status"] == "uploaded"
        print(f"Complete OK: {comp_data['message']}")

        # Verify object exists on S3
        s3_key_short = f"videos/{short_vid_id}/raw/short video.mp4"
        head_s3 = s3_client.head_object(Bucket=settings.s3_bucket_name, Key=s3_key_short)
        assert head_s3["ContentLength"] == len(short_video_bytes)
        print(f"S3 HeadObject verified: size={head_s3['ContentLength']} bytes")

        # ──────────────────────────────────────────────────────────────────────
        # TEST 2: Long Video (2 Parts, 50MB + remaining) & Resume Simulation
        # ──────────────────────────────────────────────────────────────────────
        print("\n--- [TEST 2] Long Video Multipart Upload & Resume Simulation ---")
        part_size = settings.upload_recommended_part_bytes  # 52428800 bytes (50MB)
        chunk1 = long_video_bytes[:part_size]
        chunk2 = long_video_bytes[part_size:]
        print(f"Chunk 1 size: {len(chunk1)} bytes")
        print(f"Chunk 2 size: {len(chunk2)} bytes")

        init_long_res = await client.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(lesson_long.id),
                "file_name": "long video.mp4",
                "file_size": len(long_video_bytes),
                "content_type": "video/mp4",
            },
            headers=headers,
        )
        assert init_long_res.status_code == 200
        init_long_data = init_long_res.json()
        long_vid_id = init_long_data["video_id"]
        long_upload_id = init_long_data["upload_id"]
        assert init_long_data["total_parts"] == 2
        print(f"Init OK: video_id={long_vid_id}, upload_id={long_upload_id}, total_parts=2")

        # Upload part 1
        url_part1_res = await client.post(
            "/api/admin/videos/upload",
            json={
                "video_id": long_vid_id,
                "upload_id": long_upload_id,
                "part_number": 1,
            },
            headers=headers,
        )
        assert url_part1_res.status_code == 200
        url_1 = url_part1_res.json()["presigned_url"]

        async with httpx.AsyncClient(timeout=120.0) as s3_http_client:
            put_p1 = await s3_http_client.put(
                url_1,
                content=chunk1,
                headers={"Content-Type": "video/mp4"},
            )
        assert put_p1.status_code == 200
        etag_p1 = put_p1.headers.get("ETag", "").strip('"')
        print(f"Part 1 uploaded to S3: ETag={etag_p1}")

        # Simulate network disconnect: Client re-calls /init
        print("Simulating disconnect & resume: re-calling /upload/init...")
        resume_res = await client.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(lesson_long.id),
                "file_name": "long video.mp4",
                "file_size": len(long_video_bytes),
                "content_type": "video/mp4",
            },
            headers=headers,
        )
        assert resume_res.status_code == 200
        resume_data = resume_res.json()
        assert resume_data["upload_id"] == long_upload_id
        assert resume_data["parts_uploaded"] == [1], (
            f"Expected [1], got {resume_data['parts_uploaded']}"
        )
        print(f"Resume verified! Server detected parts_uploaded: {resume_data['parts_uploaded']}")

        # Upload remaining part 2
        url_part2_res = await client.post(
            "/api/admin/videos/upload",
            json={
                "video_id": long_vid_id,
                "upload_id": long_upload_id,
                "part_number": 2,
            },
            headers=headers,
        )
        assert url_part2_res.status_code == 200
        url_2 = url_part2_res.json()["presigned_url"]

        async with httpx.AsyncClient(timeout=60.0) as s3_http_client:
            put_p2 = await s3_http_client.put(
                url_2,
                content=chunk2,
                headers={"Content-Type": "video/mp4"},
            )
        assert put_p2.status_code == 200
        etag_p2 = put_p2.headers.get("ETag", "").strip('"')
        print(f"Part 2 uploaded to S3: ETag={etag_p2}")

        # Complete multipart upload
        comp_long_res = await client.post(
            "/api/admin/videos/upload/complete",
            json={
                "video_id": long_vid_id,
                "upload_id": long_upload_id,
                "parts": [
                    {"part_number": 1, "etag": etag_p1},
                    {"part_number": 2, "etag": etag_p2},
                ],
            },
            headers=headers,
        )
        assert comp_long_res.status_code == 200, f"Complete long video failed: {comp_long_res.text}"
        print(f"Long video complete OK: {comp_long_res.json()['message']}")

        # Verify combined file on S3
        s3_key_long = f"videos/{long_vid_id}/raw/long video.mp4"
        head_s3_long = s3_client.head_object(Bucket=settings.s3_bucket_name, Key=s3_key_long)
        assert head_s3_long["ContentLength"] == len(long_video_bytes)
        print(f"S3 HeadObject verified: full assembled size={head_s3_long['ContentLength']} bytes")

        # ──────────────────────────────────────────────────────────────────────
        # TEST 3: Cancel Pipeline / Abort Multipart Session on S3
        # ──────────────────────────────────────────────────────────────────────
        print("\n--- [TEST 3] Cancel Pipeline & Abort S3 Multipart Upload ---")
        init_cancel_res = await client.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(lesson_short.id),  # Re-init on lesson_short to replace
                "file_name": "to_be_cancelled.mp4",
                "file_size": 25_000_000,
                "content_type": "video/mp4",
            },
            headers=headers,
        )
        assert init_cancel_res.status_code == 200
        cancel_vid_id = init_cancel_res.json()["video_id"]
        cancel_upload_id = init_cancel_res.json()["upload_id"]
        print(f"New session to cancel: video_id={cancel_vid_id}, upload_id={cancel_upload_id}")

        # Cancel upload
        cancel_res = await client.put(
            f"/api/admin/pipeline/{cancel_vid_id}/cancel",
            headers=headers,
        )
        assert cancel_res.status_code == 200
        print(f"Cancel response OK: {cancel_res.json()}")

        # Clean up test files from S3
        print("\nCleaning up test objects from AWS S3...")
        try:
            s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key_short)
            s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key_long)
            print("Cleaned up test objects from S3.")
        except Exception as e:
            print(f"Cleanup warning: {e}")

    print("\n" + "=" * 60)
    print("ALL E2E S3 UPLOAD TESTS PASSED SUCCESSFULLY! (C2.01 - C2.05)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
