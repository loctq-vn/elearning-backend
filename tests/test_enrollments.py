"""Integration tests for Enrollment and My Courses (B4.01 — Doc 08 §2.6, §2.8)."""

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
    Instructor,
    Lesson,
    User,
    UserRole,
)
from app.db.session import async_session_factory
from app.main import app


async def _create_student() -> tuple[User, str]:
    suffix = uuid4().hex[:8]
    async with async_session_factory() as session:
        student = User(
            id=uuid4(),
            full_name=f"Student {suffix}",
            email=f"student_enroll_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=UserRole.STUDENT,
            is_verified=True,
            is_locked=False,
        )
        session.add(student)
        await session.commit()
        token = create_access_token(student.id)
        return student, token


async def _create_course_with_curriculum(
    *, price: int = 0, status: CourseStatus = CourseStatus.PUBLISHED
) -> tuple[Course, Chapter, Lesson]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        category = Category(name=f"Category {suffix}", slug=f"cat-{suffix}")
        session.add(category)
        await session.commit()

        course = Course(
            title=f"Course Test {suffix}",
            price=price,
            status=status,
            category_id=category.id,
            thumbnail_url=f"https://cdn.example.com/thumb_{suffix}.jpg",
        )
        session.add(course)
        await session.commit()

        chapter = Chapter(course_id=course.id, title="Chương 1", order_index=0)
        session.add(chapter)
        await session.commit()

        lesson = Lesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title="Bài 1: Mở đầu",
            order_index=0,
            duration_seconds=300.0,
            is_trial_allowed=True,
        )
        session.add(lesson)
        await session.commit()

        return course, chapter, lesson


@pytest.mark.asyncio
async def test_enroll_free_course_success() -> None:
    """POST /api/courses/{id}/enroll allows enrolling into free courses (§2.6)."""
    student, token = await _create_student()
    course, _chapter, lesson = await _create_course_with_curriculum(price=0)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/courses/{course.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert "enrollment_id" in data
        assert data["course_id"] == str(course.id)
        assert data["first_lesson_id"] == str(lesson.id)
        assert "enrolled_at" in data


@pytest.mark.asyncio
async def test_enroll_paid_course_rejected() -> None:
    """POST /api/courses/{id}/enroll rejects paid courses with 400 COURSE_NOT_FREE."""
    student, token = await _create_student()
    course, _chapter, _lesson = await _create_course_with_curriculum(price=500000)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/courses/{course.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"]["code"] == "COURSE_NOT_FREE"


@pytest.mark.asyncio
async def test_enroll_duplicate_rejected() -> None:
    """POST /api/courses/{id}/enroll rejects duplicate enrollments with 409 ALREADY_ENROLLED."""
    student, token = await _create_student()
    course, _chapter, _lesson = await _create_course_with_curriculum(price=0)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res1 = await ac.post(
            f"/api/courses/{course.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 201

        res2 = await ac.post(
            f"/api/courses/{course.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 409
        data = res2.json()
        assert data["error"]["code"] == "ALREADY_ENROLLED"


@pytest.mark.asyncio
async def test_enroll_unpublished_course_rejected() -> None:
    """POST /api/courses/{id}/enroll returns 404 for draft/hidden courses."""
    student, token = await _create_student()
    course, _chapter, _lesson = await _create_course_with_curriculum(
        price=0, status=CourseStatus.DRAFT
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/courses/{course.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_my_courses_library() -> None:
    """GET /api/my-courses lists courses enrolled by current user (§2.8)."""
    student, token = await _create_student()
    course, _chapter, lesson = await _create_course_with_curriculum(price=0)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # Before enrollment: empty
        res_before = await ac.get(
            "/api/my-courses",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_before.status_code == 200
        assert res_before.json()["data"] == []

        # Enroll in course
        await ac.post(
            f"/api/courses/{course.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )

        # After enrollment: contains course
        res_after = await ac.get(
            "/api/my-courses",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_after.status_code == 200
        items = res_after.json()["data"]
        assert len(items) == 1
        item = items[0]
        assert item["course_id"] == str(course.id)
        assert item["title"] == course.title
        assert item["next_lesson_id"] == str(lesson.id)
        assert item["next_lesson_title"] == lesson.title
        assert item["progress_percent"] == 0.0

        # Filter by in_progress status
        res_in_prog = await ac.get(
            "/api/my-courses?status=in_progress",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(res_in_prog.json()["data"]) == 1

        # Filter by completed status: 0
        res_comp = await ac.get(
            "/api/my-courses?status=completed",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(res_comp.json()["data"]) == 0
