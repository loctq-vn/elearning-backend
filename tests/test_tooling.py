"""Kiểm tra tooling baseline: không cần mạng, không cần cơ sở dữ liệu."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PACKAGES = ("fastapi", "sqlalchemy", "alembic", "pgvector", "httpx", "pytest", "ruff", "mypy")
REQUIRED_ENV_KEYS = (
    "DATABASE_URL",
    "DATABASE_URL_SYNC",
    "TEST_DATABASE_URL",
    "STORAGE_ENDPOINT_URL",
    "PAYOS_CHECKSUM_KEY",
    "CORS_ORIGINS",
)
FORBIDDEN_LOCAL_CONFIG = ("localhost:9000", "pgvector/pgvector:pg16", "minio/minio")


def test_agents_rules_exist() -> None:
    assert (ROOT / "AGENTS.md").is_file(), "Thiếu AGENTS.md — file luật bắt buộc cho AI agent."


def test_requirements_lists_core_dependencies() -> None:
    content = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for package in REQUIRED_PACKAGES:
        assert package in content, f"requirements.txt thiếu gói: {package}"


def test_env_example_has_cloud_and_test_variables() -> None:
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in REQUIRED_ENV_KEYS:
        assert key in content, f".env.example thiếu biến: {key}"


def test_docs_are_cloud_only() -> None:
    """Không còn nhánh cấu hình cục bộ trong tài liệu triển khai."""
    doc = (ROOT / "docs" / "12_BE_Implementation_Guide.md").read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_LOCAL_CONFIG:
        assert forbidden not in doc, f"Còn cấu hình cục bộ trong docs/12: {forbidden}"


def test_pyproject_configures_quality_tools() -> None:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'asyncio_mode = "auto"' in content
    assert "[tool.ruff]" in content
    assert "[tool.mypy]" in content


def test_gitignore_protects_secrets() -> None:
    content = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in content
    assert "!.env.example" in content
