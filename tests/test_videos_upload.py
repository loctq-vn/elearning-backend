"""Tests for Direct S3 Video Upload (Phase C2, Contract 08 §9, Spec 11 §3.3.1)."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest

from app.core.security import create_access_token, get_password_hash
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
from app.main import app


async def _create_admin() -> tuple[User, str]:
    suffix = uuid4().hex[:8]
    async with async_session_factory() as session:
        admin = User(
            id=uuid4(),
            full_name="Admin Video Test",
            email=f"admin_vid_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=UserRole.ADMIN,
            is_verified=True,
            is_locked=False,
        )
        session.add(admin)
        await session.commit()
        token = create_access_token(admin.id)
        return admin, token


async def _create_student() -> tuple[User, str]:
    suffix = uuid4().hex[:8]
    async with async_session_factory() as session:
        student = User(
            id=uuid4(),
            full_name="Student Video Test",
            email=f"student_vid_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=UserRole.STUDENT,
            is_verified=True,
            is_locked=False,
        )
        session.add(student)
        await session.commit()
        token = create_access_token(student.id)
        return student, token


async def _create_lesson(admin_id: uuid4) -> Lesson:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        category = Category(
            name=f"Video Test Cat {suffix}",
            slug=f"video-cat-{suffix}",
        )
        session.add(category)
        await session.flush()

        course = Course(
            title=f"Video Test Course {suffix}",
            category_id=category.id,
            price=0,
            status=CourseStatus.DRAFT,
            created_by=admin_id,
        )
        session.add(course)
        await session.flush()

        chapter = Chapter(
            course_id=course.id,
            title=f"Chapter {suffix}",
            order_index=1,
        )
        session.add(chapter)
        await session.flush()

        lesson = Lesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title=f"Lesson {suffix}",
            order_index=1,
            is_trial_allowed=False,
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        return lesson


@pytest.mark.asyncio
async def test_init_upload_success_and_db_state() -> None:
    """C2.01: Initiate multipart upload, create video and 4 pipeline steps."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    with patch("app.modules.videos.service.S3StorageAdapter") as mock_adapter_cls:
        mock_storage = mock_adapter_cls.return_value
        mock_storage.find_active_multipart_upload.return_value = None
        mock_storage.create_multipart_upload.return_value = "s3-mock-upload-id-123"

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                "/api/admin/videos/upload/init",
                json={
                    "lesson_id": str(lesson.id),
                    "file_name": "bai_01_intro.mp4",
                    "file_size": 60_000_000,
                    "content_type": "video/mp4",
                },
                headers=headers,
            )

    assert res.status_code == 200
    data = res.json()
    assert "video_id" in data
    assert data["upload_id"] == "s3-mock-upload-id-123"
    assert data["part_size"] == 52428800
    assert data["total_parts"] == 2
    assert data["parts_uploaded"] == []

    # Verify database state
    async with async_session_factory() as session:
        video = await session.get(Video, data["video_id"])
        assert video is not None
        assert video.lesson_id == lesson.id
        assert video.original_filename == "bai_01_intro.mp4"
        assert video.file_size_bytes == 60_000_000
        assert video.overall_status == VideoOverallStatus.UPLOADING

        # Verify 4 pipeline steps created
        step_records = (
            await session.execute(
                PipelineStepRecord.__table__.select().where(
                    PipelineStepRecord.video_id == data["video_id"]
                )
            )
        ).all()
        assert len(step_records) == 4
        step_names = {r.step for r in step_records}
        assert step_names == {
            PipelineStep.UPLOAD.value,
            PipelineStep.TRANSCODE.value,
            PipelineStep.TRANSCRIBE.value,
            PipelineStep.INDEX.value,
        }
        for r in step_records:
            assert r.status == StepStatus.PENDING.value


@pytest.mark.asyncio
async def test_init_upload_file_too_large() -> None:
    """C2.01: Reject file larger than 5GB with 413 FILE_TOO_LARGE."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(lesson.id),
                "file_name": "huge_video.mp4",
                "file_size": 6 * 1024 * 1024 * 1024,
                "content_type": "video/mp4",
            },
            headers=headers,
        )

    assert res.status_code == 413
    assert res.json()["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_init_upload_invalid_file_format() -> None:
    """C2.01: Reject non-video file formats with 400 INVALID_FILE_FORMAT."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(lesson.id),
                "file_name": "malicious_script.exe",
                "file_size": 1024 * 1024,
                "content_type": "application/x-msdownload",
            },
            headers=headers,
        )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_FILE_FORMAT"


@pytest.mark.asyncio
async def test_init_upload_lesson_not_found() -> None:
    """C2.01: Return 404 when lesson does not exist."""
    admin, admin_token = await _create_admin()
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(uuid4()),
                "file_name": "intro.mp4",
                "file_size": 10 * 1024 * 1024,
                "content_type": "video/mp4",
            },
            headers=headers,
        )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_init_upload_forbidden_for_student() -> None:
    """C2.01: Non-admin users are forbidden from uploading videos."""
    student, student_token = await _create_student()
    lesson = await _create_lesson(student.id)
    headers = {"Authorization": f"Bearer {student_token}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/admin/videos/upload/init",
            json={
                "lesson_id": str(lesson.id),
                "file_name": "intro.mp4",
                "file_size": 10 * 1024 * 1024,
                "content_type": "video/mp4",
            },
            headers=headers,
        )

    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_init_upload_resumes_interrupted_upload() -> None:
    """C2.01 / C2.02: Resume upload after network failure, reading parts_uploaded."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    with patch("app.modules.videos.service.S3StorageAdapter") as mock_adapter_cls:
        mock_storage = mock_adapter_cls.return_value
        # First call: init
        mock_storage.find_active_multipart_upload.return_value = None
        mock_storage.create_multipart_upload.return_value = "upload-session-resume-123"

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            res1 = await ac.post(
                "/api/admin/videos/upload/init",
                json={
                    "lesson_id": str(lesson.id),
                    "file_name": "long_lecture.mp4",
                    "file_size": 100_000_000,
                    "content_type": "video/mp4",
                },
                headers=headers,
            )
            assert res1.status_code == 200

            # Second call: simulating client disconnect & resume with active S3 upload
            mock_storage.find_active_multipart_upload.return_value = (
                "videos/vid/raw/long_lecture.mp4",
                "upload-session-resume-123",
            )
            mock_storage.list_parts.return_value = [1]

            res2 = await ac.post(
                "/api/admin/videos/upload/init",
                json={
                    "lesson_id": str(lesson.id),
                    "file_name": "long_lecture.mp4",
                    "file_size": 100_000_000,
                    "content_type": "video/mp4",
                },
                headers=headers,
            )

    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["upload_id"] == "upload-session-resume-123"
    assert data2["parts_uploaded"] == [1]


@pytest.mark.asyncio
async def test_get_presigned_part_url_success() -> None:
    """C2.02: Generate presigned PUT URL for a specific part."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    with patch("app.modules.videos.service.S3StorageAdapter") as mock_adapter_cls:
        mock_storage = mock_adapter_cls.return_value
        mock_storage.find_active_multipart_upload.return_value = None
        mock_storage.create_multipart_upload.return_value = "upload-id-part-test"
        mock_storage.generate_presigned_part_url.return_value = (
            "https://s3.example.com/part-1-presigned"
        )

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            init_res = await ac.post(
                "/api/admin/videos/upload/init",
                json={
                    "lesson_id": str(lesson.id),
                    "file_name": "lecture.mp4",
                    "file_size": 60_000_000,
                    "content_type": "video/mp4",
                },
                headers=headers,
            )
            video_id = init_res.json()["video_id"]

            part_res = await ac.post(
                "/api/admin/videos/upload",
                json={
                    "video_id": video_id,
                    "upload_id": "upload-id-part-test",
                    "part_number": 1,
                },
                headers=headers,
            )

    assert part_res.status_code == 200
    part_data = part_res.json()
    assert part_data["presigned_url"] == "https://s3.example.com/part-1-presigned"
    assert "expires_at" in part_data


@pytest.mark.asyncio
async def test_get_presigned_part_url_invalid_part_number() -> None:
    """C2.02: Reject part_number out of bounds."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    with patch("app.modules.videos.service.S3StorageAdapter") as mock_adapter_cls:
        mock_storage = mock_adapter_cls.return_value
        mock_storage.find_active_multipart_upload.return_value = None
        mock_storage.create_multipart_upload.return_value = "upload-id-part-test"

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            init_res = await ac.post(
                "/api/admin/videos/upload/init",
                json={
                    "lesson_id": str(lesson.id),
                    "file_name": "lecture.mp4",
                    "file_size": 60_000_000,  # 2 parts
                    "content_type": "video/mp4",
                },
                headers=headers,
            )
            video_id = init_res.json()["video_id"]

            part_res = await ac.post(
                "/api/admin/videos/upload",
                json={
                    "video_id": video_id,
                    "upload_id": "upload-id-part-test",
                    "part_number": 99,  # Invalid (>2)
                },
                headers=headers,
            )

    assert part_res.status_code == 400
    assert part_res.json()["error"]["code"] == "INVALID_PART_NUMBER"


@pytest.mark.asyncio
async def test_complete_upload_success_and_db_state() -> None:
    """C2.03: Complete multipart upload, update raw_storage_url and step status."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    with patch("app.modules.videos.service.S3StorageAdapter") as mock_adapter_cls:
        mock_storage = mock_adapter_cls.return_value
        mock_storage.find_active_multipart_upload.return_value = None
        mock_storage.create_multipart_upload.return_value = "upload-id-complete-test"
        mock_storage.complete_multipart_upload.return_value = (
            "https://cdn.example.com/videos/raw/lecture.mp4"
        )

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            init_res = await ac.post(
                "/api/admin/videos/upload/init",
                json={
                    "lesson_id": str(lesson.id),
                    "file_name": "lecture.mp4",
                    "file_size": 60_000_000,  # 2 parts
                    "content_type": "video/mp4",
                },
                headers=headers,
            )
            video_id = init_res.json()["video_id"]

            complete_res = await ac.post(
                "/api/admin/videos/upload/complete",
                json={
                    "video_id": video_id,
                    "upload_id": "upload-id-complete-test",
                    "parts": [
                        {"part_number": 1, "etag": '"etag-part-1"'},
                        {"part_number": 2, "etag": '"etag-part-2"'},
                    ],
                },
                headers=headers,
            )

    assert complete_res.status_code == 200
    comp_data = complete_res.json()
    assert comp_data["overall_status"] == "uploaded"
    assert "hoàn tất" in comp_data["message"]

    # Verify DB state
    async with async_session_factory() as session:
        video = await session.get(Video, video_id)
        assert video.overall_status == VideoOverallStatus.UPLOADED
        assert video.raw_storage_url == "https://cdn.example.com/videos/raw/lecture.mp4"

        # Check upload step completed
        step_records = (
            await session.execute(
                PipelineStepRecord.__table__.select().where(
                    PipelineStepRecord.video_id == video_id,
                    PipelineStepRecord.step == PipelineStep.UPLOAD.value,
                )
            )
        ).all()
        assert len(step_records) == 1
        assert step_records[0].status == StepStatus.COMPLETED.value
        assert step_records[0].progress == 100.0


@pytest.mark.asyncio
async def test_complete_upload_missing_parts() -> None:
    """C2.03: Reject completion when required parts are missing."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    with patch("app.modules.videos.service.S3StorageAdapter") as mock_adapter_cls:
        mock_storage = mock_adapter_cls.return_value
        mock_storage.find_active_multipart_upload.return_value = None
        mock_storage.create_multipart_upload.return_value = "upload-id-missing-parts"

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            init_res = await ac.post(
                "/api/admin/videos/upload/init",
                json={
                    "lesson_id": str(lesson.id),
                    "file_name": "lecture.mp4",
                    "file_size": 60_000_000,  # 2 parts
                    "content_type": "video/mp4",
                },
                headers=headers,
            )
            video_id = init_res.json()["video_id"]

            complete_res = await ac.post(
                "/api/admin/videos/upload/complete",
                json={
                    "video_id": video_id,
                    "upload_id": "upload-id-missing-parts",
                    "parts": [
                        {"part_number": 1, "etag": '"etag-part-1"'},
                        # Part 2 is missing
                    ],
                },
                headers=headers,
            )

    assert complete_res.status_code == 400
    assert complete_res.json()["error"]["code"] == "MISSING_PARTS"


@pytest.mark.asyncio
async def test_cancel_pipeline_during_upload() -> None:
    """C2.03: Cancel upload session, abort multipart on S3, revert status."""
    admin, admin_token = await _create_admin()
    lesson = await _create_lesson(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    with patch("app.modules.videos.service.S3StorageAdapter") as mock_adapter_cls:
        mock_storage = mock_adapter_cls.return_value
        mock_storage.find_active_multipart_upload.return_value = None
        mock_storage.create_multipart_upload.return_value = "upload-id-cancel-test"

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            init_res = await ac.post(
                "/api/admin/videos/upload/init",
                json={
                    "lesson_id": str(lesson.id),
                    "file_name": "cancel_lecture.mp4",
                    "file_size": 20_000_000,
                    "content_type": "video/mp4",
                },
                headers=headers,
            )
            video_id = init_res.json()["video_id"]

            mock_storage.find_active_multipart_upload.return_value = (
                f"videos/{video_id}/raw/cancel_lecture.mp4",
                "upload-id-cancel-test",
            )

            cancel_res = await ac.put(
                f"/api/admin/pipeline/{video_id}/cancel",
                headers=headers,
            )

    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["message"] == "Đã hủy xử lý."
    assert cancel_data["overall_status"] == "uploaded"
    mock_storage.abort_multipart_upload.assert_called_once_with(
        key=f"videos/{video_id}/raw/cancel_lecture.mp4",
        upload_id="upload-id-cancel-test",
    )
