"""Comprehensive integration tests for authentication endpoints."""

import hashlib
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from app.db.models.schema import OtpCode, OtpPurpose, User
from app.db.session import async_session_factory, engine
from app.main import app


@pytest.mark.asyncio
async def test_auth_full_lifecycle() -> None:
    """Test full student auth lifecycle: register -> verify -> login -> refresh -> logout -> forgot -> reset."""
    unique_suffix = uuid4().hex[:8]
    test_email = f"student_{unique_suffix}@example.com"
    raw_password = "Password@123"
    new_password = "NewPassword@456"

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Register new student
            register_res = await ac.post(
                "/api/auth/register",
                json={
                    "full_name": "Nguyễn Văn Test",
                    "email": test_email,
                    "password": raw_password,
                },
            )
            assert register_res.status_code == 201, register_res.text
            reg_data = register_res.json()
            assert reg_data["email"] == test_email
            assert reg_data["otp_expires_in"] == 300

            # Retrieve the generated OTP from DB
            async with async_session_factory() as session:
                stmt = (
                    select(OtpCode)
                    .where(
                        OtpCode.email == test_email,
                        OtpCode.purpose == OtpPurpose.REGISTRATION,
                        OtpCode.used_at.is_(None),
                    )
                    .order_by(OtpCode.created_at.desc())
                )
                otp_record = (await session.execute(stmt)).scalar_one_or_none()
                assert otp_record is not None

                # Also verify user created with is_verified = False
                user_stmt = select(User).where(User.email == test_email)
                user = (await session.execute(user_stmt)).scalar_one_or_none()
                assert user is not None
                assert user.is_verified is False

            # 2. Test invalid OTP verification
            invalid_verify_res = await ac.post(
                "/api/auth/verify-otp",
                json={
                    "email": test_email,
                    "otp_code": "000000",
                    "purpose": "registration",
                },
            )
            assert invalid_verify_res.status_code == 400
            assert invalid_verify_res.json()["error"]["code"] == "INVALID_OTP"

            # Compute known OTP code for testing
            test_otp_code = "123456"
            test_otp_hash = hashlib.sha256(test_otp_code.encode("utf-8")).hexdigest()

            async with async_session_factory() as session:
                stmt = (
                    select(OtpCode)
                    .where(
                        OtpCode.email == test_email,
                        OtpCode.purpose == OtpPurpose.REGISTRATION,
                        OtpCode.used_at.is_(None),
                    )
                    .order_by(OtpCode.created_at.desc())
                )
                otp_record = (await session.execute(stmt)).scalar_one()
                otp_record.code_hash = test_otp_hash
                otp_record.attempt_count = 0
                await session.commit()

            # 3. Verify OTP successfully (auto-login)
            verify_res = await ac.post(
                "/api/auth/verify-otp",
                json={
                    "email": test_email,
                    "otp_code": test_otp_code,
                    "purpose": "registration",
                },
            )
            assert verify_res.status_code == 200, verify_res.text
            verify_data = verify_res.json()
            assert verify_data["token_type"] == "Bearer"
            assert "access_token" in verify_data
            assert "refresh_token" in verify_data

            # Verify user is now verified
            async with async_session_factory() as session:
                user_stmt = select(User).where(User.email == test_email)
                user = (await session.execute(user_stmt)).scalar_one()
                assert user.is_verified is True

            # 4. Duplicate registration should now return 409 EMAIL_ALREADY_EXISTS
            dup_reg_res = await ac.post(
                "/api/auth/register",
                json={
                    "full_name": "Nguyễn Văn Test",
                    "email": test_email,
                    "password": raw_password,
                },
            )
            assert dup_reg_res.status_code == 409
            assert dup_reg_res.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

            # 5. Login with wrong password
            wrong_login_res = await ac.post(
                "/api/auth/login",
                json={
                    "email": test_email,
                    "password": "WrongPassword@123",
                },
            )
            assert wrong_login_res.status_code == 401
            assert wrong_login_res.json()["error"]["code"] == "INVALID_CREDENTIALS"

            # 6. Login with correct password
            login_res = await ac.post(
                "/api/auth/login",
                json={
                    "email": test_email,
                    "password": raw_password,
                },
            )
            assert login_res.status_code == 200, login_res.text
            login_data = login_res.json()
            access_token = login_data["access_token"]
            refresh_token = login_data["refresh_token"]
            assert login_data["user"]["email"] == test_email
            assert login_data["user"]["role"] == "student"

            # 7. Refresh token rotation
            refresh_res = await ac.post(
                "/api/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert refresh_res.status_code == 200, refresh_res.text
            refresh_data = refresh_res.json()
            new_access_token = refresh_data["access_token"]
            new_refresh_token = refresh_data["refresh_token"]
            assert new_access_token != access_token
            assert new_refresh_token != refresh_token

            # Reusing the old rotated refresh token should fail with 401
            stale_refresh_res = await ac.post(
                "/api/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert stale_refresh_res.status_code == 401
            assert stale_refresh_res.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"

            # 8. Logout
            logout_res = await ac.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {new_access_token}"},
                json={"refresh_token": new_refresh_token},
            )
            assert logout_res.status_code == 200
            assert logout_res.json()["message"] == "Đăng xuất thành công"

            # 9. Forgot password
            forgot_res = await ac.post(
                "/api/auth/forgot-password",
                json={"email": test_email},
            )
            assert forgot_res.status_code == 200
            assert forgot_res.json()["otp_expires_in"] == 300

            # Set test OTP for password reset
            reset_otp_code = "654321"
            reset_otp_hash = hashlib.sha256(reset_otp_code.encode("utf-8")).hexdigest()

            async with async_session_factory() as session:
                stmt = (
                    select(OtpCode)
                    .where(
                        OtpCode.email == test_email,
                        OtpCode.purpose == OtpPurpose.PASSWORD_RESET,
                        OtpCode.used_at.is_(None),
                    )
                    .order_by(OtpCode.created_at.desc())
                )
                otp_record = (await session.execute(stmt)).scalar_one()
                otp_record.code_hash = reset_otp_hash
                otp_record.attempt_count = 0
                await session.commit()

            # 10. Verify OTP for password_reset to receive reset_token
            verify_reset_res = await ac.post(
                "/api/auth/verify-otp",
                json={
                    "email": test_email,
                    "otp_code": reset_otp_code,
                    "purpose": "password_reset",
                },
            )
            assert verify_reset_res.status_code == 200, verify_reset_res.text
            reset_token = verify_reset_res.json()["reset_token"]
            assert reset_token is not None

            # 11. Reset password
            reset_pass_res = await ac.post(
                "/api/auth/reset-password",
                json={
                    "reset_token": reset_token,
                    "new_password": new_password,
                },
            )
            assert reset_pass_res.status_code == 200
            assert reset_pass_res.json()["message"] == "Mật khẩu đã được đặt lại thành công."

            # 12. Login with old password fails
            old_login_res = await ac.post(
                "/api/auth/login",
                json={
                    "email": test_email,
                    "password": raw_password,
                },
            )
            assert old_login_res.status_code == 401

            # 13. Login with new password succeeds!
            new_login_res = await ac.post(
                "/api/auth/login",
                json={
                    "email": test_email,
                    "password": new_password,
                },
            )
            assert new_login_res.status_code == 200
            assert new_login_res.json()["user"]["email"] == test_email
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_auth_validation_errors() -> None:
    """Test schema validation on invalid email and weak passwords."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res1 = await ac.post(
            "/api/auth/register",
            json={
                "full_name": "A",  # too short (< 2)
                "email": "invalid-email",
                "password": "123",  # weak
            },
        )
        assert res1.status_code == 400
        assert res1.json()["error"]["code"] == "VALIDATION_ERROR"

        res2 = await ac.post(
            "/api/auth/verify-otp",
            json={
                "email": "student@example.com",
                "otp_code": "123",  # must be 6 digits
                "purpose": "invalid_purpose",
            },
        )
        assert res2.status_code == 400
        assert res2.json()["error"]["code"] == "VALIDATION_ERROR"
