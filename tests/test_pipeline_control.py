"""Tests for Video Pipeline Control APIs (Phase C3, Contract 08 §9.2 - §9.5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
            full_name="Admin Pipeline Test",
            email=f"admin_pipe_{suffix}@example.com",
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
            full_name="Student Pipeline Test",
            email=f"student_pipe_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=UserRole.STUDENT,
            is_verified=True,
            is_locked=False,
        )
        session.add(student)
        await session.commit()
        token = create_access_token(student.id)
        return student, token


async def _create_video_with_steps(
    admin_id: uuid4,
    overall_status: VideoOverallStatus = VideoOverallStatus.UPLOADED,
) -> tuple[Lesson, Video]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        category = Category(
            name=f"Pipe Test Cat {suffix}",
            slug=f"pipe-cat-{suffix}",
        )
        session.add(category)
        await session.flush()

        course = Course(
            title=f"Pipe Test Course {suffix}",
            category_id=category.id,
            price=0,
            status=CourseStatus.DRAFT,
            created_by=admin_id,
        )
        session.add(course)
        await session.flush()

        chapter = Chapter(
            course_id=course.id,
            title=f"Pipe Chapter {suffix}",
            order_index=1,
        )
        session.add(chapter)
        await session.flush()

        lesson = Lesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title=f"Pipe Lesson {suffix}",
            order_index=1,
            is_trial_allowed=False,
        )
        session.add(lesson)
        await session.flush()

        video = Video(
            id=uuid4(),
            lesson_id=lesson.id,
            original_filename="sample_video.mp4",
            file_size_bytes=10485760,
            mime_type="video/mp4",
            raw_storage_url="https://s3.example.com/sample.mp4",
            overall_status=overall_status,
        )
        session.add(video)
        await session.flush()

        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        # Add 4 standard steps
        for step_enum in (
            PipelineStep.UPLOAD,
            PipelineStep.TRANSCODE,
            PipelineStep.TRANSCRIBE,
            PipelineStep.INDEX,
        ):
            step_record = PipelineStepRecord(
                id=uuid4(),
                video_id=video.id,
                step=step_enum,
                status=StepStatus.COMPLETED
                if step_enum == PipelineStep.UPLOAD
                else StepStatus.PENDING,
                progress=100.0 if step_enum == PipelineStep.UPLOAD else 0.0,
                next_attempt_at=None if step_enum == PipelineStep.UPLOAD else future_time,
            )
            session.add(step_record)

        await session.commit()
        return lesson, video


@pytest.mark.asyncio
async def test_get_pipeline_status_success() -> None:
    admin, token = await _create_admin()
    lesson, video = await _create_video_with_steps(admin.id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/admin/pipeline/{video.id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == str(video.id)
    assert data["lesson_id"] == str(lesson.id)
    assert data["lesson_title"] == lesson.title
    assert data["overall_status"] == "uploaded"
    assert len(data["steps"]) == 4

    step_names = [s["step"] for s in data["steps"]]
    assert step_names == ["upload", "transcode", "transcribe", "index"]
    assert data["steps"][0]["status"] == "completed"
    assert data["steps"][1]["status"] == "pending"


@pytest.mark.asyncio
async def test_get_pipeline_status_forbidden_student() -> None:
    admin, _ = await _create_admin()
    student, student_token = await _create_student()
    _, video = await _create_video_with_steps(admin.id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/admin/pipeline/{video.id}/status",
            headers={"Authorization": f"Bearer {student_token}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_pipeline_status_not_found() -> None:
    admin, token = await _create_admin()
    non_existent_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/admin/pipeline/{non_existent_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_pipelines_pagination_and_filter() -> None:
    admin, token = await _create_admin()
    _, video = await _create_video_with_steps(admin.id, overall_status=VideoOverallStatus.UPLOADED)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Default listing
        response = await client.get(
            "/api/admin/pipeline?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "total" in body
        assert "page" in body
        assert body["page"] == 1

        # Filter by status
        filter_res = await client.get(
            "/api/admin/pipeline?status=uploaded",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert filter_res.status_code == 200
        f_data = filter_res.json()["data"]
        assert all(item["overall_status"] == "uploaded" for item in f_data)


@pytest.mark.asyncio
async def test_retry_pipeline_step_success() -> None:
    admin, token = await _create_admin()
    _, video = await _create_video_with_steps(admin.id, overall_status=VideoOverallStatus.FAILED)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Retry transcode step
        res = await client.post(
            f"/api/admin/pipeline/{video.id}/retry?step=transcode",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["video_id"] == str(video.id)
        assert "transcode" in data["message"]

        # Also verify backward compatible 'stt' query param
        stt_res = await client.post(
            f"/api/admin/pipeline/{video.id}/retry?step=stt",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert stt_res.status_code == 200


@pytest.mark.asyncio
async def test_retry_pipeline_invalid_step() -> None:
    admin, token = await _create_admin()
    _, video = await _create_video_with_steps(admin.id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            f"/api/admin/pipeline/{video.id}/retry?step=invalid_step_name",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_cancel_pipeline_endpoint() -> None:
    admin, token = await _create_admin()
    _, video = await _create_video_with_steps(
        admin.id, overall_status=VideoOverallStatus.PROCESSING
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.put(
            f"/api/admin/pipeline/{video.id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "Đã hủy xử lý."
        assert body["overall_status"] == "uploaded"
