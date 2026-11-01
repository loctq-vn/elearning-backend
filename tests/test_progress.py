"""Integration tests for Learning Progress & Continue Learning (B4.03, B4.04 — Doc 08 §2.2, §3.1, §3.2)."""

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
            full_name=f"Student Progress {suffix}",
            email=f"student_prog_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=UserRole.STUDENT,
            is_verified=True,
            is_locked=False,
        )
        session.add(student)
        await session.commit()
        token = create_access_token(student.id)
        return student, token


async def _setup_course_for_progress(
    *, lesson_count: int = 2
) -> tuple[Course, Chapter, list[Lesson]]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        category = Category(name=f"Cat Prog {suffix}", slug=f"cat-prog-{suffix}")
        session.add(category)
        await session.commit()

        course = Course(
            title=f"Course Prog {suffix}",
            price=0,
            status=CourseStatus.PUBLISHED,
            category_id=category.id,
            thumbnail_url=f"https://cdn.example.com/prog_thumb_{suffix}.jpg",
        )
        session.add(course)
        await session.commit()

        chapter = Chapter(course_id=course.id, title="Chương 1", order_index=0)
        session.add(chapter)
        await session.commit()

        lessons: list[Lesson] = []
        for i in range(lesson_count):
            lesson = Lesson(
                course_id=course.id,
                chapter_id=chapter.id,
                title=f"Bài {i + 1}",
                order_index=i,
                duration_seconds=100.0,
                is_trial_allowed=False,
            )
            session.add(lesson)
            lessons.append(lesson)

        await session.commit()
        for l in lessons:
            await session.refresh(l)

        return course, chapter, lessons


@pytest.mark.asyncio
async def test_save_progress_and_auto_completion() -> None:
    """POST /api/progress records position, auto-marks completed at 90%, and recalculates percent (§3.1)."""
    student, token = await _create_student()
    course, _chapter, lessons = await _setup_course_for_progress(lesson_count=2)
    lesson1, lesson2 = lessons[0], lessons[1]

    # Enroll in course
    async with async_session_factory() as session:
        enrollment = Enrollment(
            user_id=student.id,
            course_id=course.id,
            source="free",
            progress_percent=0.0,
        )
        session.add(enrollment)
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Watch 30 seconds (<90% of 100s)
        res1 = await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lesson1.id),
                "current_position": 30.0,
                "total_duration": 100.0,
                "completed": False,
            },
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["message"] == "OK"
        assert data1["course_progress_percent"] == 0.0

        # 2. Watch repeated 10s auto-save (e.g. 50s, 70s) -> verify upsert works
        res2 = await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lesson1.id),
                "current_position": 70.0,
                "total_duration": 100.0,
                "completed": False,
            },
        )
        assert res2.status_code == 200

        # 3. Watch 92 seconds (>=90%) -> auto marks completed!
        res3 = await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lesson1.id),
                "current_position": 92.0,
                "total_duration": 100.0,
                "completed": False,
            },
        )
        assert res3.status_code == 200
        data3 = res3.json()
        # 1 of 2 lessons completed = 50.0%
        assert data3["course_progress_percent"] == 50.0

        # 4. Complete lesson 2 explicitly
        res4 = await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lesson2.id),
                "current_position": 95.0,
                "total_duration": 100.0,
                "completed": True,
            },
        )
        assert res4.status_code == 200
        # 2 of 2 lessons completed = 100.0%
        assert res4.json()["course_progress_percent"] == 100.0


@pytest.mark.asyncio
async def test_progress_forbidden_if_not_enrolled() -> None:
    """POST /api/progress rejects tracking for non-enrolled non-trial lessons (§3.1)."""
    student, token = await _create_student()
    course, _ch, lessons = await _setup_course_for_progress(lesson_count=1)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lessons[0].id),
                "current_position": 10.0,
                "total_duration": 100.0,
                "completed": False,
            },
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "NOT_ENROLLED"


@pytest.mark.asyncio
async def test_progress_overview_statistics() -> None:
    """GET /api/progress/overview returns aggregated stats and course progress (§3.2)."""
    student, token = await _create_student()
    course, _ch, lessons = await _setup_course_for_progress(lesson_count=2)

    # Enroll in course
    async with async_session_factory() as session:
        enrollment = Enrollment(
            user_id=student.id,
            course_id=course.id,
            source="free",
            progress_percent=0.0,
        )
        session.add(enrollment)
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # Complete lesson 1
        await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lessons[0].id),
                "current_position": 95.0,
                "total_duration": 100.0,
                "completed": True,
            },
        )

        res = await ac.get(
            "/api/progress/overview",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_enrolled_courses"] >= 1
        assert data["total_lessons_completed"] >= 1
        assert "total_hours_watched" in data
        assert isinstance(data["courses"], list)
        matching = [c for c in data["courses"] if c["course_id"] == str(course.id)]
        assert len(matching) == 1
        c_item = matching[0]
        assert c_item["completed_lessons"] == 1
        assert c_item["total_lessons"] == 2
        assert c_item["progress_percent"] == 50.0


@pytest.mark.asyncio
async def test_continue_learning_flow() -> None:
    """GET /api/progress/continue returns active courses in progress with next lesson data (§2.2)."""
    student, token = await _create_student()
    course, _ch, lessons = await _setup_course_for_progress(lesson_count=2)
    lesson1, lesson2 = lessons[0], lessons[1]

    # Enroll in course
    async with async_session_factory() as session:
        enrollment = Enrollment(
            user_id=student.id,
            course_id=course.id,
            source="free",
            progress_percent=0.0,
        )
        session.add(enrollment)
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # Watch lesson 1 partially (45s)
        await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lesson1.id),
                "current_position": 45.0,
                "total_duration": 100.0,
                "completed": False,
            },
        )

        res = await ac.get(
            "/api/progress/continue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        items = res.json()["data"]
        matching = [i for i in items if i["course_id"] == str(course.id)]
        assert len(matching) == 1
        item = matching[0]
        assert item["next_lesson_id"] == str(lesson1.id)
        assert item["next_lesson_title"] == lesson1.title
        assert item["last_position"] == 45.0

        # Now finish lesson 1, next lesson should advance to lesson 2!
        await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lesson1.id),
                "current_position": 95.0,
                "total_duration": 100.0,
                "completed": True,
            },
        )

        res2 = await ac.get(
            "/api/progress/continue",
            headers={"Authorization": f"Bearer {token}"},
        )
        items2 = res2.json()["data"]
        matching2 = [i for i in items2 if i["course_id"] == str(course.id)]
        assert len(matching2) == 1
        assert matching2[0]["next_lesson_id"] == str(lesson2.id)
        assert matching2[0]["next_lesson_title"] == lesson2.title

        # Complete lesson 2 (100% course complete) -> course should no longer be in continue learning!
        await ac.post(
            "/api/progress",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lesson_id": str(lesson2.id),
                "current_position": 95.0,
                "total_duration": 100.0,
                "completed": True,
            },
        )

        res3 = await ac.get(
            "/api/progress/continue",
            headers={"Authorization": f"Bearer {token}"},
        )
        items3 = res3.json()["data"]
        matching3 = [i for i in items3 if i["course_id"] == str(course.id)]
        assert len(matching3) == 0
