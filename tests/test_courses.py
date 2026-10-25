"""Integration tests for Course Management (B3.02 — Doc 08 §2.1, 2.3, 2.5, 2.9, 2.10, 2.11)."""

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


async def _create_admin() -> tuple[User, str]:
    suffix = uuid4().hex[:8]
    async with async_session_factory() as session:
        admin = User(
            id=uuid4(),
            full_name="Admin Test",
            email=f"admin_course_{suffix}@example.com",
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
            full_name="Student Test",
            email=f"student_course_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=UserRole.STUDENT,
            is_verified=True,
            is_locked=False,
        )
        session.add(student)
        await session.commit()
        token = create_access_token(student.id)
        return student, token


async def _create_catalog_prerequisites() -> tuple[Category, Instructor]:
    suffix = uuid4().hex[:6]
    async with async_session_factory() as session:
        category = Category(
            name=f"Web Development {suffix}",
            slug=f"web-dev-{suffix}",
            description="Web tech",
        )
        instructor = Instructor(
            name=f"Teacher {suffix}",
            title="Senior Architect",
            email=f"teacher_{suffix}@example.com",
            is_active=True,
        )
        session.add_all([category, instructor])
        await session.commit()
        await session.refresh(category)
        await session.refresh(instructor)
        return category, instructor


@pytest.mark.asyncio
async def test_featured_courses() -> None:
    """Public GET /api/courses/featured returns published courses ordered by enrollment (§2.1)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/courses/featured")
        assert res.status_code == 200
        courses = res.json()
        assert isinstance(courses, list)
        for c in courses:
            assert "id" in c
            assert "title" in c
            assert "price" in c
            assert "enrolled_count" in c


@pytest.mark.asyncio
async def test_courses_paginated_list_and_search() -> None:
    """Public / Admin GET /api/courses with search and filters (§2.3)."""
    category, instructor = await _create_catalog_prerequisites()
    admin, admin_token = await _create_admin()
    suffix = uuid4().hex[:6]

    # Create published course and draft course
    async with async_session_factory() as session:
        c1 = Course(
            title=f"Complete React Guide {suffix}",
            description="Front-end development with React and Next.js",
            category_id=category.id,
            instructor_id=instructor.id,
            price=200000,
            status=CourseStatus.PUBLISHED,
            created_by=admin.id,
        )
        c2 = Course(
            title=f"Secret Draft Guide {suffix}",
            description="Internal content",
            category_id=category.id,
            instructor_id=instructor.id,
            price=100000,
            status=CourseStatus.DRAFT,
            created_by=admin.id,
        )
        session.add_all([c1, c2])
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # Public search should only return published course
        res_pub = await ac.get(f"/api/courses?search={suffix}")
        assert res_pub.status_code == 200
        data_pub = res_pub.json()
        titles_pub = [x["title"] for x in data_pub["data"]]
        assert f"Complete React Guide {suffix}" in titles_pub
        assert f"Secret Draft Guide {suffix}" not in titles_pub

        # Admin search with status filter can see draft courses
        res_adm = await ac.get(
            f"/api/courses?search={suffix}&status=draft",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_adm.status_code == 200
        data_adm = res_adm.json()
        titles_adm = [x["title"] for x in data_adm["data"]]
        assert f"Secret Draft Guide {suffix}" in titles_adm


@pytest.mark.asyncio
async def test_course_detail_and_lesson_locks() -> None:
    """Check course detail structure, lesson trial locking, and enrollment status (§2.5)."""
    category, instructor = await _create_catalog_prerequisites()
    admin, _ = await _create_admin()
    student, student_token = await _create_student()
    suffix = uuid4().hex[:6]

    async with async_session_factory() as session:
        course = Course(
            title=f"Python Mastery {suffix}",
            description="Learn modern Python",
            category_id=category.id,
            instructor_id=instructor.id,
            price=250000,
            status=CourseStatus.PUBLISHED,
            created_by=admin.id,
        )
        session.add(course)
        await session.flush()

        chap = Chapter(course_id=course.id, title="Chapter 1", order_index=0)
        session.add(chap)
        await session.flush()

        # Lesson 1: trial allowed
        l1 = Lesson(
            chapter_id=chap.id,
            course_id=course.id,
            title="Lesson 1 (Trial)",
            order_index=0,
            duration_seconds=300.0,
            is_trial_allowed=True,
        )
        # Lesson 2: locked
        l2 = Lesson(
            chapter_id=chap.id,
            course_id=course.id,
            title="Lesson 2 (Paid)",
            order_index=1,
            duration_seconds=600.0,
            is_trial_allowed=False,
        )
        session.add_all([l1, l2])
        await session.commit()
        course_id = course.id

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthenticated / non-enrolled user
        res_guest = await ac.get(f"/api/courses/{course_id}")
        assert res_guest.status_code == 200
        detail_guest = res_guest.json()
        assert detail_guest["is_enrolled"] is False
        assert detail_guest["total_lessons"] == 2
        assert detail_guest["total_duration"] == 900
        lessons = detail_guest["chapters"][0]["lessons"]
        assert lessons[0]["is_locked"] is False  # Trial allowed
        assert lessons[1]["is_locked"] is True   # Locked

        # 2. Enroll student and re-check locks
        async with async_session_factory() as session:
            enr = Enrollment(
                user_id=student.id,
                course_id=course_id,
                source="test",
                progress_percent=25.0,
            )
            session.add(enr)
            await session.commit()

        res_student = await ac.get(
            f"/api/courses/{course_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res_student.status_code == 200
        detail_student = res_student.json()
        assert detail_student["is_enrolled"] is True
        assert detail_student["progress_percent"] == 25.0
        enrolled_lessons = detail_student["chapters"][0]["lessons"]
        assert enrolled_lessons[0]["is_locked"] is False
        assert enrolled_lessons[1]["is_locked"] is False  # Now unlocked for enrolled user


@pytest.mark.asyncio
async def test_admin_course_crud_and_publish_rules() -> None:
    """Test admin Course creation with publish validation, updates, and deletion rules (§2.9 - §2.11)."""
    category, instructor = await _create_catalog_prerequisites()
    admin, admin_token = await _create_admin()
    student, _ = await _create_student()
    headers = {"Authorization": f"Bearer {admin_token}"}
    suffix = uuid4().hex[:6]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Fail to publish course directly on create
        res_pub_fail = await ac.post(
            "/api/admin/courses",
            data={
                "title": f"Direct Publish Course {suffix}",
                "category_id": str(category.id),
                "instructor_id": str(instructor.id),
                "price": 100000,
                "status": "published",
            },
            headers=headers,
        )
        assert res_pub_fail.status_code == 409
        assert res_pub_fail.json()["error"]["code"] == "COURSE_NOT_READY_TO_PUBLISH"

        # 2. Create as draft succeeds
        res_create = await ac.post(
            "/api/admin/courses",
            data={
                "title": f"Valid Draft Course {suffix}",
                "category_id": str(category.id),
                "instructor_id": str(instructor.id),
                "price": 120000,
                "status": "draft",
            },
            headers=headers,
        )
        assert res_create.status_code == 201
        course_id = res_create.json()["id"]

        # 3. Fail to update status to published when no chapters/lessons exist
        res_up_pub_fail = await ac.put(
            f"/api/admin/courses/{course_id}",
            data={"status": "published"},
            headers=headers,
        )
        assert res_up_pub_fail.status_code == 409
        assert res_up_pub_fail.json()["error"]["code"] == "COURSE_NOT_READY_TO_PUBLISH"

        # 4. Add chapter & lesson
        async with async_session_factory() as session:
            chap = Chapter(course_id=course_id, title="Intro", order_index=0)
            session.add(chap)
            await session.flush()
            less = Lesson(
                chapter_id=chap.id,
                course_id=course_id,
                title="Lesson 1",
                order_index=0,
            )
            session.add(less)
            await session.commit()

        # 5. Now update status to published succeeds
        res_up_pub_ok = await ac.put(
            f"/api/admin/courses/{course_id}",
            data={"status": "published"},
            headers=headers,
        )
        assert res_up_pub_ok.status_code == 200
        assert res_up_pub_ok.json()["status"] == "published"

        # 6. Delete rule: cannot delete if enrollments exist
        async with async_session_factory() as session:
            enr = Enrollment(user_id=student.id, course_id=course_id, source="test")
            session.add(enr)
            await session.commit()

        res_del_fail = await ac.delete(f"/api/admin/courses/{course_id}", headers=headers)
        assert res_del_fail.status_code == 409
        assert res_del_fail.json()["error"]["code"] == "COURSE_HAS_ENROLLMENTS"

        # 7. Delete succeeds when no enrollments
        async with async_session_factory() as session:
            db_enr = await session.get(Enrollment, enr.id)
            await session.delete(db_enr)
            await session.commit()

        res_del_ok = await ac.delete(f"/api/admin/courses/{course_id}", headers=headers)
        assert res_del_ok.status_code == 200
        assert res_del_ok.json()["course_id"] == course_id
