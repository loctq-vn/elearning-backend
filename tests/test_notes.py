"""Integration tests for Notes API (B5.01 — Doc 08 §7; Doc 09 notes; BR-14)."""

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


async def _create_user(role: UserRole = UserRole.STUDENT) -> tuple[User, str]:
    suffix = uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            id=uuid4(),
            full_name=f"User Notes {suffix}",
            email=f"user_notes_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=role,
            is_verified=True,
            is_locked=False,
        )
        session.add(user)
        await session.commit()
        token = create_access_token(user.id)
        return user, token


async def _setup_course_and_lesson(*, is_trial: bool = False) -> tuple[Course, Chapter, Lesson]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        category = Category(name=f"Cat {suffix}", slug=f"cat-note-{suffix}")
        session.add(category)
        await session.commit()

        course = Course(
            title=f"Course Notes {suffix}",
            price=299000,
            status=CourseStatus.PUBLISHED,
            category_id=category.id,
        )
        session.add(course)
        await session.commit()

        chapter = Chapter(course_id=course.id, title="Chương 1", order_index=0)
        session.add(chapter)
        await session.commit()

        lesson = Lesson(
            chapter_id=chapter.id,
            course_id=course.id,
            title="Bài 1",
            order_index=0,
            duration_seconds=300.0,
            is_trial_allowed=is_trial,
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(course)
        await session.refresh(chapter)
        await session.refresh(lesson)
        return course, chapter, lesson


async def _enroll_user(user_id: uuid4, course_id: uuid4) -> None:
    async with async_session_factory() as session:
        enrollment = Enrollment(user_id=user_id, course_id=course_id, source="free")
        session.add(enrollment)
        await session.commit()


@pytest.mark.anyio
async def test_create_and_list_notes_success() -> None:
    """Test creating notes and fetching them sorted by timestamp asc (§7.1, §7.2)."""
    student, token = await _create_user(UserRole.STUDENT)
    course, _chapter, lesson = await _setup_course_and_lesson()
    await _enroll_user(student.id, course.id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create note at timestamp 45.5
        resp1 = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Ghi chú tại phút thứ 45.5", "timestamp": 45.5},
        )
        assert resp1.status_code == 201
        data1 = resp1.json()
        assert data1["content"] == "Ghi chú tại phút thứ 45.5"
        assert data1["timestamp"] == 45.5
        assert "id" in data1
        assert "created_at" in data1

        # Create another note at earlier timestamp 10.0
        resp2 = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Ghi chú mở đầu bài học", "timestamp": 10.0},
        )
        assert resp2.status_code == 201

        # List notes for lesson -> should be sorted by timestamp asc
        list_resp = await client.get(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200
        notes = list_resp.json()["data"]
        assert len(notes) == 2
        assert notes[0]["timestamp"] == 10.0
        assert notes[0]["content"] == "Ghi chú mở đầu bài học"
        assert notes[1]["timestamp"] == 45.5
        assert notes[1]["content"] == "Ghi chú tại phút thứ 45.5"
        assert "updated_at" in notes[0]


@pytest.mark.anyio
async def test_create_note_access_control() -> None:
    """Test access control: non-enrolled user cannot create or list notes unless trial (§7.1, §7.2)."""
    _student, token = await _create_user(UserRole.STUDENT)
    _course, _chapter, lesson = await _setup_course_and_lesson(is_trial=False)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Not enrolled in paid course -> 403 NOT_ENROLLED
        resp = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Test note", "timestamp": 5.0},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_ENROLLED"

        # List also gives 403
        list_resp = await client.get(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 403
        assert list_resp.json()["error"]["code"] == "NOT_ENROLLED"

        # Non-existent lesson -> 404 LESSON_NOT_FOUND
        fake_lesson_id = uuid4()
        not_found_resp = await client.post(
            f"/api/lessons/{fake_lesson_id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Test note", "timestamp": 5.0},
        )
        assert not_found_resp.status_code == 404
        assert not_found_resp.json()["error"]["code"] == "LESSON_NOT_FOUND"


@pytest.mark.anyio
async def test_trial_lesson_allows_notes_without_enrollment() -> None:
    """Trial lesson allows notes even if not enrolled."""
    _student, token = await _create_user(UserRole.STUDENT)
    _course, _chapter, lesson = await _setup_course_and_lesson(is_trial=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Ghi chú bài học thử", "timestamp": 12.0},
        )
        assert resp.status_code == 201

        list_resp = await client.get(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()["data"]) == 1


@pytest.mark.anyio
async def test_note_privacy_isolation_between_users() -> None:
    """Test BR-14: User A cannot see User B's notes on the same lesson."""
    student_a, token_a = await _create_user(UserRole.STUDENT)
    student_b, token_b = await _create_user(UserRole.STUDENT)
    course, _chapter, lesson = await _setup_course_and_lesson()
    await _enroll_user(student_a.id, course.id)
    await _enroll_user(student_b.id, course.id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Student A creates note
        await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"content": "Ghi chú riêng của A", "timestamp": 20.0},
        )

        # Student B lists notes -> must be empty
        resp_b = await client.get(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b.status_code == 200
        assert len(resp_b.json()["data"]) == 0

        # Student A lists notes -> has 1 note
        resp_a = await client.get(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a.status_code == 200
        assert len(resp_a.json()["data"]) == 1


@pytest.mark.anyio
async def test_update_note_success_and_forbidden() -> None:
    """Test updating note (§7.3; BR-14)."""
    student_a, token_a = await _create_user(UserRole.STUDENT)
    student_b, token_b = await _create_user(UserRole.STUDENT)
    course, _chapter, lesson = await _setup_course_and_lesson()
    await _enroll_user(student_a.id, course.id)
    await _enroll_user(student_b.id, course.id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # A creates note
        create_resp = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"content": "Nội dung ban đầu", "timestamp": 15.0},
        )
        note_id = create_resp.json()["id"]

        # B attempts to edit A's note -> 403 FORBIDDEN
        resp_forbidden = await client.put(
            f"/api/notes/{note_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"content": "B muốn can thiệp ghi chú của A"},
        )
        assert resp_forbidden.status_code == 403
        assert resp_forbidden.json()["error"]["code"] == "FORBIDDEN"

        # A edits own note -> 200 OK
        resp_ok = await client.put(
            f"/api/notes/{note_id}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"content": "Nội dung sau khi đã chỉnh sửa"},
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json()["content"] == "Nội dung sau khi đã chỉnh sửa"
        assert resp_ok.json()["id"] == note_id

        # Update non-existent note -> 404 NOTE_NOT_FOUND
        resp_not_found = await client.put(
            f"/api/notes/{uuid4()}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"content": "Note không tồn tại"},
        )
        assert resp_not_found.status_code == 404
        assert resp_not_found.json()["error"]["code"] == "NOTE_NOT_FOUND"


@pytest.mark.anyio
async def test_delete_note_success_and_forbidden() -> None:
    """Test deleting note (§7.4; BR-14)."""
    student_a, token_a = await _create_user(UserRole.STUDENT)
    student_b, token_b = await _create_user(UserRole.STUDENT)
    course, _chapter, lesson = await _setup_course_and_lesson()
    await _enroll_user(student_a.id, course.id)
    await _enroll_user(student_b.id, course.id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # A creates note
        create_resp = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"content": "Ghi chú sắp xóa", "timestamp": 30.0},
        )
        note_id = create_resp.json()["id"]

        # B attempts to delete A's note -> 403 FORBIDDEN
        resp_forbidden = await client.delete(
            f"/api/notes/{note_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_forbidden.status_code == 403
        assert resp_forbidden.json()["error"]["code"] == "FORBIDDEN"

        # A deletes own note -> 200 OK
        resp_ok = await client.delete(
            f"/api/notes/{note_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json() == {"message": "Đã xóa ghi chú."}

        # Verify deletion in list
        list_resp = await client.get(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()["data"]) == 0

        # Delete non-existent note -> 404 NOTE_NOT_FOUND
        resp_not_found = await client.delete(
            f"/api/notes/{uuid4()}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_not_found.status_code == 404
        assert resp_not_found.json()["error"]["code"] == "NOTE_NOT_FOUND"


@pytest.mark.anyio
async def test_note_validation_errors() -> None:
    """Test validation errors: empty content, > 2000 chars, negative timestamp."""
    student, token = await _create_user(UserRole.STUDENT)
    course, _chapter, lesson = await _setup_course_and_lesson()
    await _enroll_user(student.id, course.id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Empty content
        resp_empty = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "", "timestamp": 10.0},
        )
        assert resp_empty.status_code == 400
        assert resp_empty.json()["error"]["code"] == "VALIDATION_ERROR"

        # Content > 2000 chars
        resp_long = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "a" * 2001, "timestamp": 10.0},
        )
        assert resp_long.status_code == 400
        assert resp_long.json()["error"]["code"] == "VALIDATION_ERROR"

        # Negative timestamp
        resp_neg = await client.post(
            f"/api/lessons/{lesson.id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Valid content", "timestamp": -5.0},
        )
        assert resp_neg.status_code == 400
        assert resp_neg.json()["error"]["code"] == "VALIDATION_ERROR"
