"""Integration tests for Lesson Player API (B4.02 — Doc 08 §2.7; Doc 10 §7.1)."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.core.security import create_access_token, get_password_hash
from app.db.models.schema import (
    Category,
    Chapter,
    Course,
    CourseStatus,
    Enrollment,
    Exam,
    ExamType,
    Lesson,
    Transcript,
    TranscriptSegment,
    User,
    UserRole,
    Video,
    VideoOverallStatus,
)
from app.db.session import async_session_factory
from app.main import app


async def _create_user(role: UserRole = UserRole.STUDENT) -> tuple[User, str]:
    suffix = uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            id=uuid4(),
            full_name=f"User {suffix}",
            email=f"user_player_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=role,
            is_verified=True,
            is_locked=False,
        )
        session.add(user)
        await session.commit()
        token = create_access_token(user.id)
        return user, token


async def _setup_course_with_video(
    *, is_trial: bool = False, video_status: VideoOverallStatus = VideoOverallStatus.COMPLETED
) -> tuple[Course, Chapter, Lesson, Video]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        category = Category(name=f"Cat {suffix}", slug=f"cat-play-{suffix}")
        session.add(category)
        await session.commit()

        course = Course(
            title=f"Course Player {suffix}",
            price=299000,
            status=CourseStatus.PUBLISHED,
            category_id=category.id,
        )
        session.add(course)
        await session.commit()

        chapter = Chapter(course_id=course.id, title="Chương Player", order_index=0)
        session.add(chapter)
        await session.commit()

        lesson = Lesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title="Bài Player 1",
            order_index=0,
            duration_seconds=360.0,
            is_trial_allowed=is_trial,
        )
        session.add(lesson)
        await session.commit()

        video = Video(
            id=uuid4(),
            lesson_id=lesson.id,
            original_filename="intro.mp4",
            file_size_bytes=1048576,
            mime_type="video/mp4",
            hls_master_url=f"https://d1ihpyg8k7hbzi.cloudfront.net/hls/{uuid4()}/master.m3u8",
            duration_seconds=360.0,
            overall_status=video_status,
        )
        session.add(video)
        await session.commit()

        # Add transcript
        transcript = Transcript(
            lesson_id=lesson.id,
            video_id=video.id,
            language="vi",
            version=1,
        )
        session.add(transcript)
        await session.commit()

        seg = TranscriptSegment(
            transcript_id=transcript.id,
            segment_index=0,
            start_time=0.0,
            end_time=5.5,
            text="Xin chào các bạn đến với khóa học.",
        )
        session.add(seg)

        # Add in-video quiz
        exam = Exam(
            title="Quiz giữa video 1",
            lesson_id=lesson.id,
            course_id=course.id,
            exam_type=ExamType.IN_VIDEO_QUIZ,
            trigger_timestamp=120.0,
        )
        session.add(exam)
        await session.commit()

        return course, chapter, lesson, video


@pytest.mark.asyncio
async def test_trial_lesson_accessible_without_enrollment() -> None:
    """GET /api/lessons/{id} allows access to trial lessons without purchasing (§2.7)."""
    student, token = await _create_user(UserRole.STUDENT)
    course, _ch, lesson, video = await _setup_course_with_video(is_trial=True)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/lessons/{lesson.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(lesson.id)
        assert data["title"] == lesson.title
        assert data["hls_stream_url"] == video.hls_master_url
        assert data["duration"] == 360
        assert len(data["transcript"]) >= 1
        assert len(data["quiz_markers"]) >= 1
        assert data["quiz_markers"][0]["timestamp"] == 120.0
        assert data["quiz_markers"][0]["is_answered"] is False


@pytest.mark.asyncio
async def test_non_trial_lesson_forbidden_without_enrollment() -> None:
    """GET /api/lessons/{id} returns 403 NOT_ENROLLED for paid lessons if not enrolled (§2.7)."""
    student, token = await _create_user(UserRole.STUDENT)
    course, _ch, lesson, _video = await _setup_course_with_video(is_trial=False)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/lessons/{lesson.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        data = res.json()
        assert data["error"]["code"] == "NOT_ENROLLED"


@pytest.mark.asyncio
async def test_enrolled_student_can_access_lesson() -> None:
    """GET /api/lessons/{id} allows enrolled students to access lessons (§2.7)."""
    student, token = await _create_user(UserRole.STUDENT)
    course, _ch, lesson, video = await _setup_course_with_video(is_trial=False)

    # Enroll student in course
    async with async_session_factory() as session:
        enrollment = Enrollment(
            user_id=student.id,
            course_id=course.id,
            source="paid",
            progress_percent=0.0,
        )
        session.add(enrollment)
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/lessons/{lesson.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(lesson.id)
        assert data["hls_stream_url"] == video.hls_master_url


@pytest.mark.asyncio
async def test_admin_can_access_any_lesson() -> None:
    """Admin has full access to any lesson without enrollment (§2.7, Doc 10 §8.1)."""
    admin, token = await _create_user(UserRole.ADMIN)
    course, _ch, lesson, video = await _setup_course_with_video(is_trial=False)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/lessons/{lesson.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["id"] == str(lesson.id)


@pytest.mark.asyncio
async def test_video_not_ready_returns_503() -> None:
    """GET /api/lessons/{id} returns 503 VIDEO_NOT_READY if video is still processing (§2.7)."""
    student, token = await _create_user(UserRole.STUDENT)
    course, _ch, lesson, _video = await _setup_course_with_video(
        is_trial=True, video_status=VideoOverallStatus.PROCESSING
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/lessons/{lesson.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 503
        data = res.json()
        assert data["error"]["code"] == "VIDEO_NOT_READY"


@pytest.mark.asyncio
async def test_lesson_not_found_returns_404() -> None:
    """GET /api/lessons/{id} returns 404 LESSON_NOT_FOUND for invalid UUID (§2.7)."""
    student, token = await _create_user(UserRole.STUDENT)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/lessons/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "LESSON_NOT_FOUND"
