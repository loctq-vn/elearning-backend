"""Fixture nền cho toàn bộ test suite của Backend.

Nguyên tắc cloud-only:
- Không có PostgreSQL cục bộ. Test tầng dữ liệu chỉ chạy khi khai báo biến môi trường
  TEST_DATABASE_URL (một Supabase project hoặc schema riêng dùng cho kiểm thử).
- Nếu TEST_DATABASE_URL để trống, mọi test cần cơ sở dữ liệu sẽ tự động SKIP
  thay vì báo lỗi.
- Không gọi dịch vụ ngoài thật: R2, OpenAI/Gemini, PayOS và SMTP đều phải được mock.
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator, Callable

import pytest

try:
    import pytest_asyncio

    async_fixture = pytest_asyncio.fixture
except ImportError:  # pragma: no cover - chỉ chạy test đồng bộ thì không cần pytest-asyncio
    async_fixture = pytest.fixture


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()

requires_db = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason=(
        "Chưa khai báo TEST_DATABASE_URL — bỏ qua test cần cơ sở dữ liệu cloud. "
        "Xem .env.example để biết cách cấu hình."
    ),
)


def _import_app() -> Any | None:
    """Nạp FastAPI app nếu khung dự án đã có app/main.py."""
    try:
        from app.main import app

        return app
    except Exception:  # pragma: no cover - khung dự án chưa được tạo
        return None


@pytest.fixture(scope="session")
def fastapi_app() -> Any:
    app = _import_app()
    if app is None:
        pytest.skip("app/main.py chưa tồn tại — hoàn thành Prompt 0 và Prompt 1 trước khi chạy test tích hợp.")
    return app


@async_fixture
async def client(fastapi_app: Any) -> AsyncIterator[Any]:
    """HTTP client chạy trong tiến trình qua ASGI transport, không cần server thật."""
    httpx = pytest.importorskip("httpx")
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@async_fixture
async def db_engine() -> AsyncIterator[Any]:
    """Engine async tới database kiểm thử trên cloud. Chỉ chạy khi có TEST_DATABASE_URL."""
    if not TEST_DATABASE_URL:
        pytest.skip("Chưa khai báo TEST_DATABASE_URL.")
    pytest.importorskip("sqlalchemy")
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@async_fixture
async def db_session(db_engine: Any) -> AsyncIterator[Any]:
    """Session trong một transaction và rollback khi kết thúc để không làm bẩn dữ liệu cloud."""
    from sqlalchemy.ext.asyncio import AsyncSession

    connection = await db_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture
def auth_headers_factory() -> Callable[..., dict[str, str]]:
    """Tạo header Bearer cho test.

    Ưu tiên dùng app.core.security khi đã tồn tại; nếu chưa, tự tạo JWT HS256 từ
    SECRET_KEY để test không phụ thuộc thứ tự triển khai.
    """

    def _build(user_id: str = "00000000-0000-0000-0000-000000000001", role: str = "student") -> dict[str, str]:
        try:
            from app.core.security import create_access_token

            token = create_access_token(subject=user_id, role=role)
        except Exception:
            jose = pytest.importorskip("jose")
            secret = os.getenv("SECRET_KEY", "test-secret-key-for-ifrs-only")
            token = jose.jwt.encode({"sub": user_id, "role": role, "type": "access"}, secret, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    return _build


@pytest.fixture
def student_headers(auth_headers_factory: Callable[..., dict[str, str]]) -> dict[str, str]:
    return auth_headers_factory(role="student")


@pytest.fixture
def admin_headers(auth_headers_factory: Callable[..., dict[str, str]]) -> dict[str, str]:
    return auth_headers_factory(role="admin")


@pytest.fixture
def mock_external_services(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    """Vô hiệu hoá lời gọi mạng thật tới R2 / AI / PayOS / SMTP.

    Trả về dict cho biết adapter nào đã được mock thành công, để test tự kiểm tra.
    """
    marked: dict[str, bool] = {}
    known_targets = {
        "storage": (
            "app.adapters.storage",
            ["upload_file", "upload_directory", "get_signed_url", "delete_file"],
        ),
        "ai": ("app.adapters.ai.llm", ["generate_answer", "chat_completion"]),
        "payos": ("app.adapters.payos", ["create_payment_link", "verify_webhook"]),
        "mailer": ("app.adapters.mailer", ["send_otp_email"]),
    }
    for name, (module_path, function_names) in known_targets.items():
        try:
            module = __import__(module_path, fromlist=["*"])
        except Exception:
            marked[name] = False
            continue
        for function_name in function_names:
            if hasattr(module, function_name):
                monkeypatch.setattr(module, function_name, lambda *args, **kwargs: None, raising=False)
        marked[name] = True
    return marked
