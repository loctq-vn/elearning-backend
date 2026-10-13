# E-Learning Backend

Backend API cho nền tảng học trực tuyến tích hợp AI, xây dựng bằng FastAPI.

## Công nghệ

- FastAPI, Uvicorn, Pydantic v2
- SQLAlchemy 2 và Alembic
- PostgreSQL + pgvector trên Amazon RDS
- Amazon S3/CloudFront cho object storage và phân phối nội dung
- Worker EC2 cho FFmpeg, Whisper, embedding và LLM

## Chạy local

Yêu cầu Python 3.10 trở lên và PostgreSQL có extension `vector` nếu chạy các luồng
có truy cập database. Cấu hình local không chứa credential cloud:

```powershell
Copy-Item .env.example .env
# Sửa DATABASE_URL/DATABASE_URL_SYNC và SECRET_KEY trong .env nếu cần
.\venv\Scripts\python.exe -m pip install -e ".[dev]"
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Kiểm tra:

- `GET http://127.0.0.1:8000/health` — health check
- `GET http://127.0.0.1:8000/api` — API root
- `http://127.0.0.1:8000/docs` — OpenAPI

Chạy smoke test:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Kiểm tra kết nối S3:

```powershell
# Không in hoặc commit access key/secret key.
.\venv\Scripts\python.exe -m app.adapters.storage
```

Lệnh trên gọi `HeadBucket` bằng credentials trong `.env` và không yêu cầu
bucket public. Bài kiểm tra tích hợp tương đương có thể chạy bằng:

```powershell
$env:RUN_S3_INTEGRATION = "1"
.\venv\Scripts\python.exe -m pytest tests/test_storage.py -m integration -q
```

Chỉ chạy kiểm tra tích hợp sau khi đã cấu hình credentials mới trong môi trường
local hoặc secret manager. Giữ `Block all public access` bật khi ứng dụng dùng
IAM credentials/presigned URL.

## Database migration

Alembic đọc URL từ `DATABASE_URL_SYNC` trong environment thông qua
`app/core/config.py`; không đặt connection string trong `alembic.ini`.

```powershell
.\venv\Scripts\alembic.exe upgrade head
.\venv\Scripts\alembic.exe revision --autogenerate -m "describe change"
```

## Baseline staging seed

The baseline seed is intentionally limited to system settings, one verified
admin account, categories, instructors, and draft/hidden course structure. It
does not create media URLs, video records, transcripts, embeddings, payment
records, or user activity data. Run it only after the database migration:

```powershell
$env:SEED_ADMIN_EMAIL = "admin@example.test"
$env:SEED_ADMIN_PASSWORD = "use-a-staging-password"
.\venv\Scripts\python.exe -m app.db.seed
```

`SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` are required and are never stored
in the repository. The seed is idempotent and updates records identified by
their stable email, slug, name, or title.

Trong staging, đặt `APP_ENV=staging`, dùng RDS PostgreSQL/pgvector và cung cấp
`DATABASE_URL`, `DATABASE_URL_SYNC` cùng các secret qua secret manager hoặc
environment của EC2. Chạy migration trước khi khởi động API/worker:

```powershell
$env:APP_ENV = "staging"
.\venv\Scripts\alembic.exe upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment variables và secrets

`.env.example` là danh sách biến được hỗ trợ và chỉ chứa giá trị mẫu. `.env` bị
gitignore và chỉ dùng cho máy local. Không commit API key, password, JWT secret,
credential S3, PayOS checksum key hoặc SMTP password; staging/production phải
đọc chúng từ secret manager/environment triển khai. Cấu hình cloud chính thức
theo [tài liệu kiến trúc](docs/10_BE_Architecture_AWS_EC2.md), không dùng
database/object storage bền vững cục bộ trên EC2.
