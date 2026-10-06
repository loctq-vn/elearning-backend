# E-Learning Backend

Backend API cho nền tảng học trực tuyến tích hợp AI, xây dựng bằng FastAPI.

## Công nghệ

- FastAPI, Uvicorn, Pydantic v2
- SQLAlchemy 2 và Alembic
- PostgreSQL + pgvector trên Amazon RDS
- Amazon S3/CloudFront cho object storage và phân phối nội dung

## Chạy local

```powershell
Copy-Item .env.example .env
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000/health` để kiểm tra và `http://127.0.0.1:8000/docs` để xem OpenAPI.

Các module hiện mới là skeleton theo [Architecture §6.2](docs/10_BE_Architecture_AWS_EC2.md).

