"""Integration tests for Instructor Management (B3.04 — Doc 08 §2.14)."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.core.security import create_access_token, get_password_hash
from app.db.models.schema import Course, CourseStatus, Instructor, User, UserRole
from app.db.session import async_session_factory
from app.main import app


async def _create_admin() -> tuple[User, str]:
    suffix = uuid4().hex[:8]
    async with async_session_factory() as session:
        admin = User(
            id=uuid4(),
            full_name="Admin Test",
            email=f"admin_inst_{suffix}@example.com",
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
            email=f"student_inst_{suffix}@example.com",
            password_hash=get_password_hash("Password@123"),
            role=UserRole.STUDENT,
            is_verified=True,
            is_locked=False,
        )
        session.add(student)
        await session.commit()
        token = create_access_token(student.id)
        return student, token


@pytest.mark.asyncio
async def test_instructors_dropdown_options() -> None:
    """Public GET /api/instructors/options returns lightweight instructor list (§2.14f)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/instructors/options")
        assert res.status_code == 200
        options = res.json()
        assert isinstance(options, list)
        for opt in options:
            assert "id" in opt
            assert "name" in opt
            assert "title" in opt
            assert "avatar_url" in opt


@pytest.mark.asyncio
async def test_admin_instructors_list_and_filters() -> None:
    """Admin GET /api/admin/instructors with pagination, status filter, and search (§2.14a)."""
    _, admin_token = await _create_admin()
    _, student_token = await _create_student()
    headers = {"Authorization": f"Bearer {admin_token}"}
    suffix = uuid4().hex[:6]

    # Create test instructors
    async with async_session_factory() as session:
        i1 = Instructor(
            name=f"Prof Active {suffix}",
            title="Senior Lecturer",
            email=f"active_{suffix}@university.edu",
            is_active=True,
        )
        i2 = Instructor(
            name=f"Prof Suspended {suffix}",
            title="Adjunct Lecturer",
            email=f"suspended_{suffix}@university.edu",
            is_active=False,
        )
        session.add_all([i1, i2])
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # Non-admin forbidden
        res_forbidden = await ac.get(
            "/api/admin/instructors",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res_forbidden.status_code == 403

        # List all
        res_all = await ac.get("/api/admin/instructors?page=1&page_size=20", headers=headers)
        assert res_all.status_code == 200
        data_all = res_all.json()
        assert "data" in data_all
        assert data_all["total"] >= 2

        # Filter active
        res_act = await ac.get(
            f"/api/admin/instructors?status=active&search={suffix}", headers=headers
        )
        assert res_act.status_code == 200
        items_act = res_act.json()["data"]
        assert len(items_act) == 1
        assert items_act[0]["name"] == f"Prof Active {suffix}"

        # Filter suspended
        res_susp = await ac.get(
            f"/api/admin/instructors?status=suspended&search={suffix}", headers=headers
        )
        assert res_susp.status_code == 200
        items_susp = res_susp.json()["data"]
        assert len(items_susp) == 1
        assert items_susp[0]["name"] == f"Prof Suspended {suffix}"


@pytest.mark.asyncio
async def test_admin_instructor_crud_and_delete_rules() -> None:
    """Test Create -> Detail -> Update -> Deletion rules for instructors (§2.14)."""
    admin, admin_token = await _create_admin()
    headers = {"Authorization": f"Bearer {admin_token}"}
    suffix = uuid4().hex[:6]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create instructor
        inst_name = f"Dr. Lê Hoàng {suffix}"
        res_create = await ac.post(
            "/api/admin/instructors",
            data={
                "name": inst_name,
                "title": "Chuyên gia AI & Data Science",
                "bio": "10 năm kinh nghiệm nghiên cứu Machine Learning.",
                "email": f"lehoang_{suffix}@example.com",
                "phone": "0987654321",
                "is_active": "true",
            },
            headers=headers,
        )
        assert res_create.status_code == 201, res_create.text
        inst_data = res_create.json()
        inst_id = inst_data["id"]
        assert inst_data["name"] == inst_name

        # 2. Get instructor detail
        res_detail = await ac.get(f"/api/admin/instructors/{inst_id}", headers=headers)
        assert res_detail.status_code == 200
        assert res_detail.json()["email"] == f"lehoang_{suffix}@example.com"
        assert res_detail.json()["courses"] == []

        # 3. Update instructor
        new_title = "Giám đốc Nghiên cứu AI"
        res_update = await ac.put(
            f"/api/admin/instructors/{inst_id}",
            data={"title": new_title},
            headers=headers,
        )
        assert res_update.status_code == 200
        assert res_update.json()["title"] == new_title

        # 4. Deletion Rule 1: Block when has active published course
        async with async_session_factory() as session:
            pub_course = Course(
                title=f"Advanced Deep Learning {suffix}",
                instructor_id=inst_id,
                status=CourseStatus.PUBLISHED,
                price=500000,
                created_by=admin.id,
            )
            session.add(pub_course)
            await session.commit()
            pub_course_id = pub_course.id

        res_del_blocked = await ac.delete(
            f"/api/admin/instructors/{inst_id}", headers=headers
        )
        assert res_del_blocked.status_code == 400
        assert res_del_blocked.json()["error"]["code"] == "INSTRUCTOR_HAS_ACTIVE_COURSES"

        # 5. Deletion Rule 2: Deactivate (soft suspended) when only draft courses exist
        async with async_session_factory() as session:
            c = await session.get(Course, pub_course_id)
            c.status = CourseStatus.DRAFT
            await session.commit()

        res_deact = await ac.delete(
            f"/api/admin/instructors/{inst_id}", headers=headers
        )
        assert res_deact.status_code == 200
        deact_data = res_deact.json()
        assert deact_data["deleted"] is False

        # Verify instructor is_active is now False
        res_check = await ac.get(f"/api/admin/instructors/{inst_id}", headers=headers)
        assert res_check.json()["is_active"] is False

        # 6. Deletion Rule 3: Soft delete when no courses linked
        async with async_session_factory() as session:
            c = await session.get(Course, pub_course_id)
            c.deleted_at = c.created_at  # mark course deleted
            await session.commit()

        res_soft_del = await ac.delete(
            f"/api/admin/instructors/{inst_id}", headers=headers
        )
        assert res_soft_del.status_code == 200
        del_data = res_soft_del.json()
        assert del_data["deleted"] is True

        # Verify instructor is now 404
        res_not_found = await ac.get(f"/api/admin/instructors/{inst_id}", headers=headers)
        assert res_not_found.status_code == 404
