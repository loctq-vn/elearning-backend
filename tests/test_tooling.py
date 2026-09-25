"""Kiểm tra tooling baseline: không cần mạng, không cần cơ sở dữ liệu."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PACKAGES = (
    "fastapi",
    "sqlalchemy",
    "alembic",
    "pgvector",
    "httpx",
    "pytest",
    "ruff",
    "mypy",
    "faster-whisper",
    "tiktoken",
)
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


# --- Kiểm chứng các quyết định thiết kế đã chốt (Prompts 1-22) ---


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def test_db_schema_specifies_columns_for_every_table() -> None:
    """docs/09: cả 27 bảng đều phải có bảng cột đầy đủ (5 cột)."""
    content = _read("docs/09_BE_Database_Schema.md")
    column_tables = content.count("|---|---|---|---|---|")
    assert column_tables >= 27, f"Chỉ có {column_tables} bảng đặc tả cột, cần ít nhất 27."


def test_db_schema_has_trigger_timestamp_and_renamed_ai_column() -> None:
    content = _read("docs/09_BE_Database_Schema.md")
    assert "trigger_timestamp" in content, "Thiếu exams.trigger_timestamp → quiz giữa video không chạy được."
    assert "| current_timestamp |" not in content, "Còn cột current_timestamp trùng tên hàm SQL chuẩn."
    assert "video_position_seconds" in content
    assert "prompt_version" in content
    assert "lease_expires_at" in content, "Thiếu cột lease cho vòng đời job worker."


def test_contract_has_authorization_matrix_for_all_endpoints() -> None:
    """docs/08 Phụ lục E phải phủ đủ 75 endpoint."""
    content = _read("docs/08_FE_BE_Data_Contract.md")
    section = _section(content, "## PHỤ LỤC E", "## TỔNG HỢP THỐNG KÊ")
    rows = [line for line in section.splitlines() if line.startswith("| ") and "/api/" in line]
    assert len(rows) == 75, f"Ma trận phân quyền có {len(rows)} dòng, cần đúng 75."


def test_contract_has_json_examples_appendix() -> None:
    content = _read("docs/08_FE_BE_Data_Contract.md")
    section = _section(content, "## PHỤ LỤC F", "## TỔNG HỢP THỐNG KÊ")
    assert section.count("```json") >= 8, "Phụ lục F cần ít nhất 8 ví dụ JSON."


def test_out_of_scope_returns_200_not_error() -> None:
    contract = _read("docs/08_FE_BE_Data_Contract.md")
    pipeline = _read("docs/11_BE_AI_Pipeline_Spec.md")
    assert "is_out_of_scope" in contract
    assert "(ngừng dùng)" in contract, "AI_OUT_OF_SCOPE phải được đánh dấu ngừng dùng."
    assert "is_out_of_scope = true" in pipeline


def test_pipeline_spec_has_upload_protocol_hls_and_whisper() -> None:
    pipeline = _read("docs/11_BE_AI_Pipeline_Spec.md")
    assert "presigned" in pipeline, "Thiếu giao thức upload presigned multipart."
    assert "-hls_time 6" in pipeline, "Thiếu tham số encode HLS."
    assert "faster-whisper" in pipeline, "Thiếu cấu hình Whisper cục bộ."
    assert "int8" in pipeline and "float16" in pipeline


def test_pipeline_spec_has_time_weighting_formula() -> None:
    pipeline = _read("docs/11_BE_AI_Pipeline_Spec.md")
    assert "d' = d - w * max(0, 1 - |s - t| / W)" in pipeline, "Thiếu công thức tăng trọng thời gian."
    assert "retrieval_time_weight" in pipeline


def test_architecture_spec_has_job_lifecycle() -> None:
    architecture = _read("docs/10_BE_Architecture.md")
    assert "SKIP LOCKED" in architecture, "Thiếu cơ chế nhận việc chống chạy trùng."
    assert "lease" in architecture


def test_prompt_chain_has_no_deprecated_error_code() -> None:
    chain = _read("docs/BE_Coding_Prompt_Chain.md")
    assert "EXAM_MAX_ATTEMPTS_REACHED" not in chain, "Còn mã lỗi cũ, phải dùng 403 MAX_ATTEMPTS_REACHED."


def test_agents_rules_cover_data_conventions() -> None:
    content = _read("AGENTS.md")
    for expected in ("Asia/Ho_Chi_Minh", "tiktoken", "is_out_of_scope", "SKIP LOCKED", "Phụ lục E"):
        assert expected in content, f"AGENTS.md thiếu quy ước: {expected}"

