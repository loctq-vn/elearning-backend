"""Comprehensive integration tests for Users & Profile module (B2.01, B2.02, B2.03)."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.db.models.schema import Course, CourseStatus, Enrollment, RefreshToken, User, UserRole
from app.db.session import async_session_factory
from app.main import app


async def _create_test_user(
    *,
    full_name: str,
    email: str,
    password: str = "Password@123",
    role: UserRole = UserRole.STUDENT,
    is_verified: bool = True,
    is_locked: bool = False,
    avatar_url: str | None = None,
) -> User:
    """Helper to persist a user for integration tests."""
    async with async_session_factory() as session:
        user = User(
            id=uuid4(),
            full_name=full_name,
            email=email.strip().lower(),
            password_hash=get_password_hash(password),
            role=role,
            is_verified=is_verified,
            is_locked=is_locked,
            avatar_url=avatar_url,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# =========================================================================
# B2.01 — Profile APIs Tests
# =========================================================================


@pytest.mark.asyncio
async def test_get_my_profile_success() -> None:
    """Test GET /api/users/me returns authenticated user's profile with envelope."""
    suffix = uuid4().hex[:8]
    user = await _create_test_user(
        full_name="Nguyễn Văn A",
        email=f"profile_{suffix}@example.com",
    )
    token = create_access_token(user.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["message"] == "OK"
        profile = data["data"]
        assert profile["id"] == str(user.id)
        assert profile["full_name"] == "Nguyễn Văn A"
        assert profile["email"] == user.email
        assert profile["role"] == "student"
        assert "password_hash" not in profile


@pytest.mark.asyncio
async def test_get_my_profile_unauthorized() -> None:
    """Test GET /api/users/me without Bearer token returns 401 UNAUTHORIZED."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/users/me")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_update_my_profile_name() -> None:
    """Test PUT /api/users/me updating full_name."""
    suffix = uuid4().hex[:8]
    user = await _create_test_user(
        full_name="Tên Cũ",
        email=f"update_{suffix}@example.com",
    )
    token = create_access_token(user.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            data={"full_name": "Tên Đã Cập Nhật"},
        )
        assert res.status_code == 200, res.text
        profile = res.json()["data"]
        assert profile["full_name"] == "Tên Đã Cập Nhật"

        # Verify DB persisted
        async with async_session_factory() as session:
            db_user = (await session.execute(select(User).where(User.id == user.id))).scalar_one()
            assert db_user.full_name == "Tên Đã Cập Nhật"


@pytest.mark.asyncio
async def test_update_my_profile_name_validation() -> None:
    """Test PUT /api/users/me with too short full_name returns 400 VALIDATION_ERROR."""
    suffix = uuid4().hex[:8]
    user = await _create_test_user(
        full_name="Nguyễn Văn",
        email=f"val_{suffix}@example.com",
    )
    token = create_access_token(user.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            data={"full_name": "A"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_update_my_profile_with_avatar_success() -> None:
    """Test PUT /api/users/me with avatar upload using S3StorageAdapter."""
    suffix = uuid4().hex[:8]
    user = await _create_test_user(
        full_name="Lê Văn Avatar",
        email=f"avatar_{suffix}@example.com",
    )
    token = create_access_token(user.id)

    dummy_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    files = {"avatar": ("avatar.png", io.BytesIO(dummy_png_bytes), "image/png")}

    expected_url = f"https://cdn.example.com/avatars/{user.id}/avatar_test.png"

    with patch("app.adapters.storage.S3StorageAdapter.upload_file", return_value=expected_url):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.put(
                "/api/users/me",
                headers={"Authorization": f"Bearer {token}"},
                data={"full_name": "Lê Văn Avatar Mới"},
                files=files,
            )
            assert res.status_code == 200, res.text
            profile = res.json()["data"]
            assert profile["full_name"] == "Lê Văn Avatar Mới"
            assert profile["avatar_url"] == expected_url


@pytest.mark.asyncio
async def test_update_my_profile_avatar_invalid_type() -> None:
    """Test PUT /api/users/me rejecting non-image avatar format."""
    suffix = uuid4().hex[:8]
    user = await _create_test_user(
        full_name="Nguyễn Văn Type",
        email=f"invalid_type_{suffix}@example.com",
    )
    token = create_access_token(user.id)

    files = {"avatar": ("document.txt", io.BytesIO(b"Hello text"), "text/plain")}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_update_my_profile_avatar_too_large() -> None:
    """Test PUT /api/users/me rejecting avatar larger than 2MB."""
    suffix = uuid4().hex[:8]
    user = await _create_test_user(
        full_name="Nguyễn Văn Size",
        email=f"toolarge_{suffix}@example.com",
    )
    token = create_access_token(user.id)

    oversized_bytes = b"0" * (2 * 1024 * 1024 + 10)  # > 2MB
    files = {"avatar": ("large.png", io.BytesIO(oversized_bytes), "image/png")}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "FILE_TOO_LARGE"


# =========================================================================
# Change Password Tests
# =========================================================================


@pytest.mark.asyncio
async def test_change_password_success() -> None:
    """Test PUT /api/users/me/password successfully updates password and allows login."""
    suffix = uuid4().hex[:8]
    raw_old = "OldPassword@123"
    raw_new = "NewPassword@456"
    user = await _create_test_user(
        full_name="Nguyễn Văn Pass",
        email=f"pwd_{suffix}@example.com",
        password=raw_old,
    )
    token = create_access_token(user.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # Change password
        res = await ac.put(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": raw_old,
                "new_password": raw_new,
            },
        )
        assert res.status_code == 200, res.text
        assert res.json()["message"] == "Đổi mật khẩu thành công."

        # Verify old password no longer works
        old_login = await ac.post(
            "/api/auth/login",
            json={"email": user.email, "password": raw_old},
        )
        assert old_login.status_code == 401

        # Verify new password works
        new_login = await ac.post(
            "/api/auth/login",
            json={"email": user.email, "password": raw_new},
        )
        assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current() -> None:
    """Test PUT /api/users/me/password with wrong current password returns 400 WRONG_CURRENT_PASSWORD."""
    suffix = uuid4().hex[:8]
    user = await _create_test_user(
        full_name="Nguyễn Văn Wrong",
        email=f"wrong_cur_{suffix}@example.com",
        password="Password@123",
    )
    token = create_access_token(user.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "IncorrectPassword@123",
                "new_password": "NewValidPassword@456",
            },
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "WRONG_CURRENT_PASSWORD"


@pytest.mark.asyncio
async def test_change_password_same_as_old() -> None:
    """Test PUT /api/users/me/password when new password matches old password."""
    suffix = uuid4().hex[:8]
    raw_old = "Password@123"
    user = await _create_test_user(
        full_name="Nguyễn Văn Same",
        email=f"same_pwd_{suffix}@example.com",
        password=raw_old,
    )
    token = create_access_token(user.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": raw_old,
                "new_password": raw_old,
            },
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "SAME_AS_OLD_PASSWORD"


@pytest.mark.asyncio
async def test_change_password_too_weak() -> None:
    """Test PUT /api/users/me/password rejecting weak passwords with 400 PASSWORD_TOO_WEAK."""
    suffix = uuid4().hex[:8]
    raw_old = "Password@123"
    user = await _create_test_user(
        full_name="Nguyễn Văn Weak",
        email=f"weak_pwd_{suffix}@example.com",
        password=raw_old,
    )
    token = create_access_token(user.id)

    weak_passwords = [
        "short",  # < 8 chars
        "alllowercase123!",  # no uppercase
        "ALLUPPERCASE123!",  # no lowercase
        "NoDigitsHere!",  # no digits
        "NoSpecialChar123",  # no special char
    ]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        for weak_pass in weak_passwords:
            res = await ac.put(
                "/api/users/me/password",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "current_password": raw_old,
                    "new_password": weak_pass,
                },
            )
            assert res.status_code == 400
            assert res.json()["error"]["code"] == "PASSWORD_TOO_WEAK"


# =========================================================================
# B2.02 — Admin User Controls Tests
# =========================================================================


@pytest.mark.asyncio
async def test_admin_list_users_pagination_search_and_filter() -> None:
    """Test GET /api/admin/users pagination, search and status filtering."""
    suffix = uuid4().hex[:8]
    admin = await _create_test_user(
        full_name="Admin Boss",
        email=f"admin_{suffix}@example.com",
        role=UserRole.ADMIN,
    )
    admin_token = create_access_token(admin.id)

    # Create students with distinct states and keywords
    keyword = f"kw_{suffix}"
    s1 = await _create_test_user(
        full_name=f"Student One {keyword}",
        email=f"s1_{suffix}@example.com",
        is_verified=True,
        is_locked=False,
    )
    s2 = await _create_test_user(
        full_name=f"Student Two {keyword}",
        email=f"s2_{suffix}@example.com",
        is_verified=True,
        is_locked=True,
    )
    s3 = await _create_test_user(
        full_name="Unverified User",
        email=f"s3_{keyword}@example.com",
        is_verified=False,
        is_locked=False,
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Search keyword
        search_res = await ac.get(f"/api/admin/users?search={keyword}", headers=headers)
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert search_data["total"] >= 3
        returned_ids = {u["id"] for u in search_data["data"]}
        assert {str(s1.id), str(s2.id), str(s3.id)}.issubset(returned_ids)

        # 2. Filter status: locked
        locked_res = await ac.get(f"/api/admin/users?search={keyword}&status=locked", headers=headers)
        assert locked_res.status_code == 200
        locked_data = locked_res.json()
        assert all(u["is_locked"] is True for u in locked_data["data"])
        assert any(u["id"] == str(s2.id) for u in locked_data["data"])
        assert not any(u["id"] == str(s1.id) for u in locked_data["data"])

        # 3. Filter status: unverified
        unverified_res = await ac.get(
            f"/api/admin/users?search={keyword}&status=unverified",
            headers=headers,
        )
        assert unverified_res.status_code == 200
        unverified_data = unverified_res.json()
        assert all(u["is_verified"] is False for u in unverified_data["data"])
        assert any(u["id"] == str(s3.id) for u in unverified_data["data"])

        # 4. Pagination
        page_res = await ac.get(
            f"/api/admin/users?search={keyword}&page=1&page_size=2",
            headers=headers,
        )
        assert page_res.status_code == 200
        page_data = page_res.json()
        assert page_data["page"] == 1
        assert page_data["page_size"] == 2
        assert len(page_data["data"]) == 2
        assert page_data["total_pages"] >= 2


@pytest.mark.asyncio
async def test_admin_list_users_enrolled_courses_count() -> None:
    """Test GET /api/admin/users properly computes enrolled_courses_count."""
    suffix = uuid4().hex[:8]
    admin = await _create_test_user(
        full_name="Admin Enrolls",
        email=f"admin_enroll_{suffix}@example.com",
        role=UserRole.ADMIN,
    )
    admin_token = create_access_token(admin.id)

    student = await _create_test_user(
        full_name=f"Enrolled Student {suffix}",
        email=f"student_enroll_{suffix}@example.com",
    )

    # Insert a course and enrollment
    async with async_session_factory() as session:
        course = Course(
            id=uuid4(),
            title=f"Khóa học Test {suffix}",
            price=100000,
            status=CourseStatus.PUBLISHED,
        )
        session.add(course)
        await session.flush()

        enrollment = Enrollment(
            id=uuid4(),
            user_id=student.id,
            course_id=course.id,
            source="test",
        )
        session.add(enrollment)
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {admin_token}"}
        res = await ac.get(f"/api/admin/users?search={student.email}", headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == str(student.id)
        assert data[0]["enrolled_courses_count"] == 1


@pytest.mark.asyncio
async def test_admin_lock_and_unlock_student_workflow() -> None:
    """Test full lock and unlock cycle, session revocation, and API access denial."""
    suffix = uuid4().hex[:8]
    admin = await _create_test_user(
        full_name="Admin Sec",
        email=f"admin_sec_{suffix}@example.com",
        role=UserRole.ADMIN,
    )
    admin_token = create_access_token(admin.id)

    student = await _create_test_user(
        full_name="Student To Lock",
        email=f"locked_stud_{suffix}@example.com",
    )
    student_token = create_access_token(student.id)

    # Simulate active refresh token
    async with async_session_factory() as session:
        refresh_token = RefreshToken(
            id=uuid4(),
            user_id=student.id,
            token_hash=f"hash_{suffix}",
            expires_at=datetime.now(timezone.utc),
        )
        session.add(refresh_token)
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        student_headers = {"Authorization": f"Bearer {student_token}"}

        # 1. Lock student
        lock_res = await ac.put(f"/api/admin/users/{student.id}/lock", headers=admin_headers)
        assert lock_res.status_code == 200, lock_res.text
        lock_data = lock_res.json()["data"]
        assert lock_data["is_locked"] is True
        assert lock_data["user_id"] == str(student.id)

        # Verify DB state: is_locked == True & refresh token revoked
        async with async_session_factory() as session:
            db_user = (await session.execute(select(User).where(User.id == student.id))).scalar_one()
            assert db_user.is_locked is True

            tokens = (
                await session.execute(
                    select(RefreshToken).where(RefreshToken.user_id == student.id)
                )
            ).scalars().all()
            assert all(t.revoked_at is not None for t in tokens)

        # 2. Student attempts calling /api/users/me while locked -> 403 FORBIDDEN
        student_res = await ac.get("/api/users/me", headers=student_headers)
        assert student_res.status_code == 403
        assert student_res.json()["error"]["code"] == "FORBIDDEN"

        # 3. Unlock student
        unlock_res = await ac.put(f"/api/admin/users/{student.id}/unlock", headers=admin_headers)
        assert unlock_res.status_code == 200, unlock_res.text
        unlock_data = unlock_res.json()["data"]
        assert unlock_data["is_locked"] is False

        # Verify student can call /api/users/me again
        student_res_after = await ac.get("/api/users/me", headers=student_headers)
        assert student_res_after.status_code == 200
        assert student_res_after.json()["data"]["id"] == str(student.id)


@pytest.mark.asyncio
async def test_admin_cannot_lock_self() -> None:
    """Test Admin attempting to lock themselves returns 409 CANNOT_LOCK_ADMIN_SELF."""
    suffix = uuid4().hex[:8]
    admin = await _create_test_user(
        full_name="Admin Self",
        email=f"admin_self_{suffix}@example.com",
        role=UserRole.ADMIN,
    )
    admin_token = create_access_token(admin.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            f"/api/admin/users/{admin.id}/lock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "CANNOT_LOCK_ADMIN_SELF"


@pytest.mark.asyncio
async def test_admin_cannot_lock_another_admin() -> None:
    """Test Admin attempting to lock another Admin returns 403 FORBIDDEN."""
    suffix = uuid4().hex[:8]
    admin1 = await _create_test_user(
        full_name="Admin One",
        email=f"admin1_{suffix}@example.com",
        role=UserRole.ADMIN,
    )
    admin2 = await _create_test_user(
        full_name="Admin Two",
        email=f"admin2_{suffix}@example.com",
        role=UserRole.ADMIN,
    )
    admin1_token = create_access_token(admin1.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            f"/api/admin/users/{admin2.id}/lock",
            headers={"Authorization": f"Bearer {admin1_token}"},
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_lock_nonexistent_user() -> None:
    """Test Admin locking non-existent user ID returns 404 NOT_FOUND."""
    suffix = uuid4().hex[:8]
    admin = await _create_test_user(
        full_name="Admin 404",
        email=f"admin_404_{suffix}@example.com",
        role=UserRole.ADMIN,
    )
    admin_token = create_access_token(admin.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        random_id = uuid4()
        res = await ac.put(
            f"/api/admin/users/{random_id}/lock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"


# =========================================================================
# RBAC Tests
# =========================================================================


@pytest.mark.asyncio
async def test_rbac_student_cannot_access_admin_endpoints() -> None:
    """Test student token cannot call any /api/admin/users endpoints (403 FORBIDDEN)."""
    suffix = uuid4().hex[:8]
    student = await _create_test_user(
        full_name="Normal Student",
        email=f"student_rbac_{suffix}@example.com",
        role=UserRole.STUDENT,
    )
    student_token = create_access_token(student.id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {student_token}"}

        list_res = await ac.get("/api/admin/users", headers=headers)
        assert list_res.status_code == 403
        assert list_res.json()["error"]["code"] == "FORBIDDEN"

        lock_res = await ac.put(f"/api/admin/users/{uuid4()}/lock", headers=headers)
        assert lock_res.status_code == 403
        assert lock_res.json()["error"]["code"] == "FORBIDDEN"

        unlock_res = await ac.put(f"/api/admin/users/{uuid4()}/unlock", headers=headers)
        assert unlock_res.status_code == 403
        assert unlock_res.json()["error"]["code"] == "FORBIDDEN"
