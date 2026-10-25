"""Integration tests for Category System (B3.01 — Doc 08 §2.4)."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.core.security import create_access_token, get_password_hash
from app.db.models.schema import Category, Course, CourseStatus, User, UserRole
from app.db.session import async_session_factory
from app.main import app


async def _create_admin() -> tuple[User, str]:
    suffix = uuid4().hex[:8]
    async with async_session_factory() as session:
        admin = User(
            id=uuid4(),
            full_name="Admin Test",
            email=f"admin_{suffix}@example.com",
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
            email=f"student_{suffix}@example.com",
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
async def test_list_categories_public() -> None:
    """Public GET /api/categories returns CategoryListResponse with course_count."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/categories")
        assert res.status_code == 200
        data = res.json()["data"]
        assert isinstance(data, list)
        for cat in data:
            assert "id" in cat
            assert "name" in cat
            assert "course_count" in cat
            assert isinstance(cat["course_count"], int)


@pytest.mark.asyncio
async def test_admin_category_crud_lifecycle() -> None:
    """Test full Category CRUD: Create -> Update -> Delete."""
    _, admin_token = await _create_admin()
    _, student_token = await _create_student()
    headers = {"Authorization": f"Bearer {admin_token}"}
    suffix = uuid4().hex[:6]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Non-admin forbidden
        res_forbidden = await ac.post(
            "/api/admin/categories",
            json={"name": f"Mobile Dev {suffix}", "slug": f"mobile-dev-{suffix}"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res_forbidden.status_code == 403

        # 2. Admin create category
        cat_name = f"Mobile Dev {suffix}"
        cat_slug = f"mobile-dev-{suffix}"
        res_create = await ac.post(
            "/api/admin/categories",
            json={
                "name": cat_name,
                "slug": cat_slug,
                "description": "Lập trình ứng dụng di động",
            },
            headers=headers,
        )
        assert res_create.status_code == 201
        created_cat = res_create.json()
        assert created_cat["name"] == cat_name
        assert created_cat["slug"] == cat_slug
        cat_id = created_cat["id"]

        # Duplicate slug check
        res_dup = await ac.post(
            "/api/admin/categories",
            json={"name": f"Another Name {suffix}", "slug": cat_slug},
            headers=headers,
        )
        assert res_dup.status_code == 409

        # 3. Update category
        updated_name = f"Flutter & React Native {suffix}"
        res_update = await ac.put(
            f"/api/admin/categories/{cat_id}",
            json={"name": updated_name, "description": "Updated desc"},
            headers=headers,
        )
        assert res_update.status_code == 200
        assert res_update.json()["name"] == updated_name

        # 4. Delete category (should succeed since no courses assigned)
        res_delete = await ac.delete(f"/api/admin/categories/{cat_id}", headers=headers)
        assert res_delete.status_code == 200
        assert res_delete.json()["category_id"] == cat_id


@pytest.mark.asyncio
async def test_admin_category_delete_blocked_when_has_courses() -> None:
    """Cannot delete a category if active courses are assigned to it."""
    admin, admin_token = await _create_admin()
    headers = {"Authorization": f"Bearer {admin_token}"}
    suffix = uuid4().hex[:6]

    async with async_session_factory() as session:
        cat = Category(
            name=f"DevOps {suffix}",
            slug=f"devops-{suffix}",
            description="DevOps engineering",
        )
        session.add(cat)
        await session.flush()

        course = Course(
            title=f"Docker & Kubernetes {suffix}",
            category_id=cat.id,
            status=CourseStatus.PUBLISHED,
            price=150000,
            created_by=admin.id,
        )
        session.add(course)
        await session.commit()
        cat_id = cat.id

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.delete(f"/api/admin/categories/{cat_id}", headers=headers)
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "CATEGORY_HAS_COURSES"
