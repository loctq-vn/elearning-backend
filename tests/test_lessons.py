"""Integration tests for Chapter and Lesson Management (B3.03 — Doc 08 §2.12, §2.13)."""

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
    Lesson,
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
            full_name="Admin Test",
            email=f"admin_less_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=UserRole.ADMIN,
            is_verified=True,
            is_locked=False,
        )
        session.add(admin)
        await session.commit()
        token = create_access_token(admin.id)
        return admin, token


async def _create_test_course(admin_id: uuid4) -> Course:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        category = Category(
            name=f"Lesson Test Cat {suffix}",
            slug=f"lesson-cat-{suffix}",
        )
        session.add(category)
        await session.flush()

        course = Course(
            title=f"Lesson Test Course {suffix}",
            category_id=category.id,
            price=0,
            status=CourseStatus.DRAFT,
            created_by=admin_id,
        )
        session.add(course)
        await session.commit()
        await session.refresh(course)
        return course


@pytest.mark.asyncio
async def test_chapter_crud_and_cascade_safeguard() -> None:
    """Test Chapter creation, update, and active video cascade safeguard (§2.12a-c)."""
    admin, admin_token = await _create_admin()
    course = await _create_test_course(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create chapter
        res_chap = await ac.post(
            f"/api/admin/courses/{course.id}/chapters",
            json={"title": "Chương 1: Mở đầu", "order": 0},
            headers=headers,
        )
        assert res_chap.status_code == 201, res_chap.text
        chap_data = res_chap.json()
        chap_id = chap_data["id"]
        assert chap_data["title"] == "Chương 1: Mở đầu"
        assert chap_data["order"] == 0

        # 2. Update chapter
        res_up = await ac.put(
            f"/api/admin/chapters/{chap_id}",
            json={"title": "Chương 1: Kiến thức nền tảng"},
            headers=headers,
        )
        assert res_up.status_code == 200
        assert res_up.json()["title"] == "Chương 1: Kiến thức nền tảng"

        # 3. Add lesson with completed video into this chapter
        async with async_session_factory() as session:
            lesson = Lesson(
                chapter_id=chap_id,
                course_id=course.id,
                title="Bài 1.1: Video quan trọng",
                order_index=0,
            )
            session.add(lesson)
            await session.flush()

            video = Video(
                id=uuid4(),
                lesson_id=lesson.id,
                original_filename="lesson1.mp4",
                file_size_bytes=1024000,
                mime_type="video/mp4",
                overall_status=VideoOverallStatus.COMPLETED,
            )
            session.add(video)
            await session.commit()
            lesson_id = lesson.id
            video_id = video.id

        # 4. Attempt to delete chapter -> must be blocked by safeguard
        res_del_block = await ac.delete(f"/api/admin/chapters/{chap_id}", headers=headers)
        assert res_del_block.status_code == 409
        assert res_del_block.json()["error"]["code"] == "CHAPTER_HAS_ACTIVE_VIDEO"

        # 5. Remove video record -> now delete succeeds
        async with async_session_factory() as session:
            v = await session.get(Video, video_id)
            await session.delete(v)
            await session.commit()

        res_del_ok = await ac.delete(f"/api/admin/chapters/{chap_id}", headers=headers)
        assert res_del_ok.status_code == 200
        assert res_del_ok.json()["chapter_id"] == chap_id


@pytest.mark.asyncio
async def test_reorder_chapters_and_lessons() -> None:
    """Test reordering chapters and nested lessons (§2.12d)."""
    admin, admin_token = await _create_admin()
    course = await _create_test_course(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with async_session_factory() as session:
        c1 = Chapter(course_id=course.id, title="Chap 1", order_index=0)
        c2 = Chapter(course_id=course.id, title="Chap 2", order_index=1)
        session.add_all([c1, c2])
        await session.flush()

        l1 = Lesson(chapter_id=c1.id, course_id=course.id, title="Less 1", order_index=0)
        l2 = Lesson(chapter_id=c1.id, course_id=course.id, title="Less 2", order_index=1)
        session.add_all([l1, l2])
        await session.commit()
        c1_id, c2_id, l1_id, l2_id = c1.id, c2.id, l1.id, l2.id

    # Swap chapters and swap lesson order / move lesson between chapters
    reorder_payload = {
        "chapters": [
            {
                "id": str(c2_id),
                "order": 0,
                "lessons": [{"id": str(l2_id), "order": 0}],
            },
            {
                "id": str(c1_id),
                "order": 1,
                "lessons": [{"id": str(l1_id), "order": 0}],
            },
        ]
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            f"/api/admin/courses/{course.id}/reorder",
            json=reorder_payload,
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["message"] == "Sắp xếp lại thành công."

    # Verify DB state
    async with async_session_factory() as session:
        db_c2 = await session.get(Chapter, c2_id)
        db_c1 = await session.get(Chapter, c1_id)
        assert db_c2.order_index == 0
        assert db_c1.order_index == 1

        db_l2 = await session.get(Lesson, l2_id)
        assert db_l2.chapter_id == c2_id
        assert db_l2.order_index == 0


@pytest.mark.asyncio
async def test_lesson_crud_lifecycle() -> None:
    """Test Lesson creation, update, and deletion (§2.13)."""
    admin, admin_token = await _create_admin()
    course = await _create_test_course(admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with async_session_factory() as session:
        chap = Chapter(course_id=course.id, title="Test Chap", order_index=0)
        session.add(chap)
        await session.commit()
        chap_id = chap.id

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create lesson without video
        res_create = await ac.post(
            f"/api/admin/chapters/{chap_id}/lessons",
            data={
                "title": "Bài học 1: Giới thiệu cú pháp",
                "description": "Nội dung chi tiết bài học",
                "is_trial_allowed": "true",
            },
            headers=headers,
        )
        assert res_create.status_code == 201, res_create.text
        created_data = res_create.json()
        lesson_id = created_data["id"]
        assert created_data["title"] == "Bài học 1: Giới thiệu cú pháp"
        assert created_data["video_id"] is None

        # 2. Update lesson
        res_update = await ac.put(
            f"/api/admin/lessons/{lesson_id}",
            data={
                "title": "Bài học 1: Cú pháp cơ bản đã cập nhật",
                "order": 5,
            },
            headers=headers,
        )
        assert res_update.status_code == 200
        updated_data = res_update.json()
        assert updated_data["title"] == "Bài học 1: Cú pháp cơ bản đã cập nhật"
        assert updated_data["order"] == 5
        assert updated_data["is_trial_allowed"] is True

        # 3. Delete lesson
        res_del = await ac.delete(f"/api/admin/lessons/{lesson_id}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.json()["lesson_id"] == lesson_id
