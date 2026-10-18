from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    raw_pass = "SecurePass@123"
    hashed = get_password_hash(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_tokens():
    user_id = uuid4()
    access_token = create_access_token(user_id)
    payload = decode_token(access_token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"

    refresh_token = create_refresh_token(user_id)
    refresh_payload = decode_token(refresh_token, expected_type="refresh")
    assert refresh_payload["sub"] == str(user_id)
    assert refresh_payload["type"] == "refresh"

def test_jwt_token_type_mismatch():
    user_id = uuid4()
    access_token = create_access_token(user_id)
    with pytest.raises(AppError) as exc_info:
        decode_token(access_token, expected_type="refresh")
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"

def test_jwt_expired_token():
    user_id = uuid4()
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-10))
    with pytest.raises(AppError) as exc_info:
        decode_token(expired_token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "TOKEN_EXPIRED"
