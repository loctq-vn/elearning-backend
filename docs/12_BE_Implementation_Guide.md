# 12 — Hướng Dẫn Triển Khai Backend Chi Tiết (Backend Implementation Guide)

> **Dự án:** Nền tảng học trực tuyến thông minh tích hợp AI Trợ giảng tương tác theo ngữ cảnh bài giảng.  
> **Phiên bản:** 1.0 — Ngày tạo: 20/09/2026  
> **Nguồn tham chiếu bắt buộc:**  
> - [`08_FE_BE_Data_Contract.md`](file:///d:/elearning-backend/docs/08_FE_BE_Data_Contract.md) (Hợp đồng API & Mã lỗi)  
> - [`09_BE_Database_Schema.md`](file:///d:/elearning-backend/docs/09_BE_Database_Schema.md) (Lược đồ 27 bảng & pgvector)  
> - [`10_BE_Architecture.md`](file:///d:/elearning-backend/docs/10_BE_Architecture.md) (Kiến trúc phân tầng & Vòng đời yêu cầu)  
> - [`11_BE_AI_Pipeline_Spec.md`](file:///d:/elearning-backend/docs/11_BE_AI_Pipeline_Spec.md) (Quy trình Video HLS, Whisper, Chunking & RAG)  

---

## 1. Mục Đích & Tổng Quan Lộ Trình

Tài liệu này là cẩm nang hướng dẫn kỹ thuật từng bước (Step-by-Step Implementation Roadmap) dành cho lập trình viên Backend để hiện thực hóa toàn bộ hệ thống Backend cho Đồ án 1.

Quá trình triển khai được chia thành **8 giai đoạn tuần tự**:
```
Giai đoạn 0: Chuẩn bị Hạ tầng & Biến môi trường (Supabase, Storage, API Keys)
    │
    ▼
Giai đoạn 1: Khởi tạo Base Project FastAPI, Cấu hình Core & Chuẩn hóa Error Handler
    │
    ▼
Giai đoạn 2: Định nghĩa SQLAlchemy Models & Khởi tạo Migration Alembic (27 bảng)
    │
    ▼
Giai đoạn 3: Triển khai Tầng Dịch vụ Xác thực (Auth, OTP, JWT, Middleware Quyền)
    │
    ▼
Giai đoạn 4: Triển khai Nghiệp vụ Khóa học, Bài giảng, Tiến độ học & Ghi chú
    │
    ▼
Giai đoạn 5: Triển khai Ngân hàng Đề thi, Quiz giữa video & Bài tập cuối bài
    │
    ▼
Giai đoạn 6: Triển khai Worker Xử lý Video (FFmpeg HLS) & Phiên âm (Whisper STT)
    │
    ▼
Giai đoạn 7: Triển khai Trí tuệ Nhân tạo (pgvector Search, RAG Q&A, Tóm tắt AI)
    │
    ▼
Giai đoạn 8: Tích hợp Cổng thanh toán PayOS, Webhook Idempotency & Dashboard Admin
```

---

## GIAI ĐOẠN 0: Chuẩn Bị Hạ Tầng & Dịch Vụ Môi Trường

### 0.0 Cloud Stack chính thức (đã chốt)
Cloud stack của dự án đã được chốt thống nhất trên toàn bộ tài liệu ở giai đoạn hiện tại, không mô tả theo dạng nhiều lựa chọn:

| Thành phần | Công nghệ chốt |
|---|---|
| Database | Supabase PostgreSQL + pgvector |
| Object Storage | Cloudflare R2 |
| Backend API | FastAPI |
| Worker | Worker nền xử lý background/pipeline |
| Video processing | FFmpeg + ffprobe |
| STT | Whisper |
| Embedding | OpenAI text-embedding-3-small (1536 chiều) |
| LLM | GPT-4o-mini (chính), Gemini Flash (dự phòng) |

Luồng pipeline chính được mô tả thống nhất:
```text
Client → FastAPI → Supabase PostgreSQL/pgvector + Cloudflare R2 → Worker → FFmpeg/Whisper/Embedding/LLM
```

Quy định đi kèm:
- Supabase và Cloudflare R2 là stack Cloud chính thức của dự án; không viết lại theo dạng "Supabase hoặc AWS", "R2 hoặc MinIO".
- Cloud-mode 100%: mọi môi trường (dev/test/prod) dùng chung Supabase PostgreSQL + pgvector và Cloudflare R2; không tạo cơ sở dữ liệu hay lưu trữ cục bộ (không container pgvector, không MinIO).
- AWS không được đưa vào pipeline hiện tại; chỉ ghi nhận là hướng migration trong tương lai thông qua Storage Adapter/AI Adapter (xem `10_BE_Architecture.md` DE-06).

### 0.1 Cài đặt môi trường phát triển cục bộ (Local Dev)
- **Python:** Phiên bản `>= 3.11` (khuyến nghị 3.11 hoặc 3.12).
- **FFmpeg:** Cài đặt FFmpeg trên máy chủ/máy dev, cấu hình đường dẫn `ffmpeg` và `ffprobe` vào biến `PATH` hệ thống.
- **PostgreSQL & pgvector:**
  - *Cloud (chính thức):* Tạo dự án mới trên **Supabase** (gói Free). Supabase đã tích hợp sẵn PostgreSQL 15+ và cho phép bật extension `vector` chỉ với 1 click trong mục Database -> Extensions.
  - Mọi môi trường kết nối trực tiếp tới Supabase này (kể cả khi lập trình cục bộ); không chạy PostgreSQL cục bộ hay container pgvector.
- **Lưu trữ đối tượng (Object Storage):** **Cloudflare R2** là storage chính thức duy nhất (miễn phí băng thông ra - Egress Free, 10GB lưu trữ miễn phí), dùng thống nhất cho mọi môi trường (dev/test/staging/production). Không dùng storage cục bộ.
- **Dịch vụ tích hợp bên ngoài:**
  - **OpenAI API Key** (dùng `text-embedding-3-small` 1536 chiều và `gpt-4o-mini`).
  - **Google Gemini API Key** (dùng `gemini-1.5-flash` làm mô hình fallback).
  - **Tài khoản PayOS** (Lấy `PAYOS_CLIENT_ID`, `PAYOS_API_KEY`, `PAYOS_CHECKSUM_KEY`).
  - **Dịch vụ gửi thư điện tử (Email SMTP / Resend API)** để gửi OTP 6 số.

### 0.2 Cấu hình tệp biến môi trường (`.env`)
Tạo tệp `.env` tại thư mục gốc với các khóa sau:
```ini
# Application
APP_ENV=development
APP_NAME="AI E-Learning Platform"
API_PREFIX=/api
SECRET_KEY=your-super-secret-jwt-key-min-32-chars
ACCESS_TOKEN_EXPIRE_SECONDS=900       # 15 phút (BR-03)
REFRESH_TOKEN_EXPIRE_DAYS=7          # 7 ngày cho Mobile

# Database (Supabase PostgreSQL + pgvector — cloud chính thức, dùng cho mọi môi trường)
DATABASE_URL=postgresql+asyncpg://postgres:your-password@db.supabase.co:5432/postgres
DATABASE_URL_SYNC=postgresql://postgres:your-password@db.supabase.co:5432/postgres # Dùng cho Alembic
# Database PHỤC VỤ TEST (tùy chọn): chỉ điền khi muốn chạy test tầng dữ liệu. Nếu để trống, các test cần DB sẽ tự động SKIP.
TEST_DATABASE_URL=postgresql+asyncpg://postgres:your-password@db.supabase.co:5432/postgres
TEST_DATABASE_URL_SYNC=postgresql://postgres:your-password@db.supabase.co:5432/postgres

# Cloudflare R2 Storage (cloud chính thức, dùng cho mọi môi trường)
STORAGE_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
STORAGE_ACCESS_KEY=your-access-key
STORAGE_SECRET_KEY=your-secret-key
STORAGE_BUCKET_NAME=elearning-media
STORAGE_PUBLIC_BASE_URL=https://media.yourdomain.com

# AI Services
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIzaSy...
AI_PRIMARY_MODEL=gpt-4o-mini
AI_FALLBACK_MODEL=gemini-1.5-flash
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# PayOS Payment (Dự kiến)
PAYOS_CLIENT_ID=...
PAYOS_API_KEY=...
PAYOS_CHECKSUM_KEY=...

# Email Service (Gửi mã OTP)
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=re_...
EMAILS_FROM_EMAIL=no-reply@yourdomain.com
```

---

## GIAI ĐOẠN 1: Khởi Tạo Base Project & Kiến Trúc Phân Tầng

### 1.1 Khởi tạo Project & Cài đặt Dependencies
Tạo môi trường ảo và cài đặt các thư viện lõi:
```bash
python -m venv venv
# Kích hoạt venv (Windows: venv\Scripts\activate, Linux/Mac: source venv/bin/activate)
pip install fastapi uvicorn[standard] pydantic[email] pydantic-settings
pip install sqlalchemy[asyncio] asyncpg psycopg2-binary alembic pgvector
pip install python-jose[cryptography] passlib[bcrypt] python-multipart
pip install httpx aiofiles boto3 celery redis payos
```

### 1.2 Thiết lập cấu trúc thư mục chuẩn theo [`10_BE_Architecture.md`](file:///d:/Đồ án 1/10_BE_Architecture.md#L125)
```text
app/
├── main.py                     # Khởi tạo FastAPI App, CORS, Error Handlers
├── core/
│   ├── config.py               # Pydantic Settings đọc từ .env
│   ├── security.py             # Hash bcrypt, tạo/giải mã JWT token
│   ├── permissions.py          # Middleware & Depends: get_current_user, require_admin, require_enrolled
│   ├── rate_limit.py           # Giới hạn tần suất request (SlowAPI hoặc Redis)
│   └── errors.py               # Custom Exception & Error Response chuẩn hóa
├── db/
│   ├── session.py              # Async SQLAlchemy Engine & SessionLocal
│   ├── base.py                 # DeclarativeBase chung
│   └── models/                 # Chứa 27 models SQLAlchemy
├── modules/                    # Phân chia theo nghiệp vụ
│   ├── auth/                   # router.py, schemas.py, service.py, repository.py
│   ├── users/
│   ├── courses/
│   ├── lessons/
│   ├── videos/
│   ├── transcripts/
│   ├── ai/
│   ├── exams/
│   ├── notes/
│   ├── progress/
│   ├── orders/
│   ├── notifications/
│   └── analytics/
├── workers/                    # Chứa logic tác vụ nền (FastAPI BackgroundTasks hoặc Celery)
│   ├── video_pipeline.py       # FFmpeg transcode HLS, Whisper STT
│   ├── reindex.py              # Chunking & Vector re-indexing
│   └── order_expiry.py         # Quét đơn hết hạn 15 phút
└── adapters/                   # Tích hợp dịch vụ biên ngoài
    ├── storage.py              # Storage Adapter: Cloudflare R2 (upload, signed URL), dùng cho mọi môi trường
    ├── mailer.py               # Gửi email OTP
    ├── payos.py                # Wrapper SDK PayOS, tạo QR VietQR
    └── ai/
        ├── whisper.py          # Whisper speech-to-text wrapper
        ├── embeddings.py       # Vector embedding client (1536 dim)
        ├── llm.py              # LLM client (GPT-4o-mini + fallback Gemini Flash)
        └── prompts/            # Bản mẫu prompt kiểm soát ngữ cảnh RAG
```

### 1.3 Chuẩn hóa Exception Handler theo [`08_FE_BE_Data_Contract.md`](file:///d:/Đồ án 1/08_FE_BE_Data_Contract.md#L28)
Xây dựng lớp `AppException` và middleware bắt lỗi toàn cục trong `app/core/errors.py`:
- Mọi lỗi phải trả về đúng định dạng JSON:
  ```json
  {
    "error": {
      "code": "ERROR_CODE_IN_SCREAMING_SNAKE_CASE",
      "message": "Thông điệp lỗi tiếng Việt thân thiện",
      "details": null
    }
  }
  ```
- Bắt `RequestValidationError` của Pydantic để trả về HTTP 400 `VALIDATION_ERROR` kèm chi tiết field lỗi.

### 1.4 Thiết kế Storage Adapter & AI Adapter (chống khóa vào nhà cung cấp)
Cloud stack hiện tại đã chốt là Supabase + Cloudflare R2, nhưng toàn bộ thao tác lưu trữ và gọi AI phải đi qua adapter để sau này chuyển sang AWS (hoặc nhà cung cấp khác) mà không phải sửa business logic:

1. **Storage Adapter (`app/adapters/storage.py`):**
   - Định nghĩa interface (abstract class) `StorageAdapter` với các phương thức chuẩn: `upload_file`, `upload_directory` (cho thư mục HLS chứa `m3u8`/`ts`), `get_signed_url`, `delete_file`.
   - Hiện thực `R2StorageAdapter` (boto3 cấu hình endpoint Cloudflare R2 qua biến `STORAGE_*`) là adapter lưu trữ duy nhất của dự án, dùng cho mọi môi trường. Nếu sau này cần chuyển sang AWS S3 (hướng migration tương lai, không dùng ở giai đoạn hiện tại), chỉ viết thêm adapter mới mà không sửa business logic.
   - Service/Worker chỉ inject `StorageAdapter` qua Dependency Injection, không import boto3 trực tiếp và không giữ transaction DB mở khi chờ phản hồi mạng.
2. **AI Adapter (`app/adapters/ai/`):**
   - `whisper.py` (STT), `embeddings.py` (text-embedding-3-small, 1536 chiều), `llm.py` (GPT-4o-mini + fallback Gemini Flash: thử mô hình chính 1 lần, lỗi 429/503/timeout thì fallback đúng 1 lần, tổng ≤ 60s).
   - Service/Worker chỉ gọi interface của adapter; thay đổi nhà cung cấp AI chỉ cần viết adapter mới, không sửa business logic.

---

## GIAI ĐOẠN 2: Lược Đồ Cơ Sở Dữ Liệu & Alembic Migrations

### 2.1 Viết Models SQLAlchemy theo [`09_BE_Database_Schema.md`](file:///d:/Đồ án 1/09_BE_Database_Schema.md)
Tạo đầy đủ 27 bảng trong thư mục `app/db/models/`:
1. `user.py`: `users`, `otp_codes`, `refresh_tokens`.
2. `course.py`: `categories`, `courses`, `chapters`, `lessons`.
3. `video.py`: `videos`, `pipeline_steps`, `transcripts`, `transcript_segments`.
4. `ai_knowledge.py`: `lesson_chunks`, `chunk_embeddings` (dùng `from pgvector.sqlalchemy import Vector`).
5. `learning.py`: `enrollments`, `lesson_progress`, `notes`.
6. `exam.py`: `questions`, `question_options`, `exams`, `exam_questions`, `exercise_attempts`, `attempt_answers`.
7. `commerce_ops.py`: `orders`, `ai_qa_logs`, `ai_summaries`, `notifications`, `system_settings`.

### 2.2 Cấu hình Alembic & Tạo chỉ mục HNSW
1. Khởi tạo Alembic: `alembic init alembic`
2. Trong `alembic/env.py`, import `Base` từ `app.db.base` và trỏ `target_metadata = Base.metadata`.
3. Thêm lệnh tạo extension `pgvector` vào đầu script migration đầu tiên:
   ```python
   op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
   ```
4. Tạo các chỉ mục quan trọng:
   - Unique Index: `op.create_index('uq_users_email', 'users', [sa.text('LOWER(email)')], unique=True)`
   - HNSW Index cho vector:
     ```python
     op.execute("""
     CREATE INDEX ix_emb_v1 ON chunk_embeddings 
     USING hnsw (embedding vector_cosine_ops) 
     WHERE embedding_version = 'v1';
     """)
     ```
5. Chạy migration: `alembic upgrade head`
6. Viết script `seed.py` tạo tài khoản Admin mặc định, các danh mục ban đầu và nạp tham số vận hành vào bảng `system_settings`.

---

## GIAI ĐOẠN 3: Triển Khai Module Xác Thực & Phân Quyền (Auth)

### 3.1 Luồng Đăng ký & OTP
1. **Endpoint `POST /api/auth/register`:**
   - Validate email hợp lệ, mật khẩu $\ge 8$ ký tự (chữ hoa, chữ thường, số, ký tự đặc biệt).
   - Kiểm tra email chưa tồn tại trong `users` (nếu có trả `409 EMAIL_ALREADY_EXISTS`).
   - Sinh mã OTP 6 chữ số ngẫu nhiên, băm mã lưu vào bảng `otp_codes` (hạn 300 giây).
   - Gọi `mailer.py` gửi OTP qua email cho học viên.
2. **Endpoint `POST /api/auth/verify-otp`:**
   - Kiểm tra OTP còn hạn, số lần thử sai `< 5`.
   - Nếu `purpose == "registration"`: Chuyển `is_verified = True`, tạo tài khoản học viên, sinh cặp JWT `access_token` (900s) và `refresh_token` (7 ngày), trả về client để tự động đăng nhập.
   - Nếu `purpose == "password_reset"`: Trả về `reset_token` dùng một lần.

### 3.2 Luồng Đăng nhập & Quản lý phiên
1. **Endpoint `POST /api/auth/login`:**
   - Kiểm tra email, mật khẩu qua bcrypt.
   - Kiểm tra tài khoản không bị khóa (`is_locked == False`) và đã xác minh email.
   - Cơ chế 1 thiết bị cho học viên: Thu hồi (`revoked_at = now()`) các refresh token cũ của user trong bảng `refresh_tokens`, lưu refresh token mới.
2. **Endpoint `POST /api/auth/refresh`:**
   - Kiểm tra refresh token hợp lệ và chưa bị thu hồi $\rightarrow$ Cấp mới access token và xoay vòng (rotate) refresh token.
3. **Middleware & Dependency Injection (`app/core/permissions.py`):**
   - `get_current_user`: Giải mã JWT Bearer, nạp thông tin user.
   - `require_admin`: Chặn `403 FORBIDDEN` nếu `role != 'admin'`.
   - `require_enrolled(lesson_id)`: Kiểm tra bài học có cho phép học thử (`is_trial_allowed`) hay không; nếu không, kiểm tra user đã có bản ghi trong bảng `enrollments` chưa, nếu chưa trả `403 NOT_ENROLLED`.

---

## GIAI ĐOẠN 4: Module Khóa Học, Bài Giảng, Tiến Độ & Ghi Chú

### 4.1 Quản lý Khóa học & Cấu trúc bài giảng
1. **Duyệt khóa học (`GET /api/courses` & `GET /api/courses/{id}`):**
   - Học viên chỉ xem được các khóa học có trạng thái `published`.
   - Admin xem được cả `draft`, `published`, `hidden`.
   - Trả về danh sách cây chương (`chapters`) và bài giảng (`lessons`) bên trong.
2. **Kiểm duyệt xuất bản khóa học (BR-06):**
   - Khi Admin đổi status sang `published`: Service kiểm tra khóa học phải có tối thiểu 1 chương và tất cả bài giảng bên trong đều có video ở trạng thái `completed`. Nếu không thỏa mãn, ném lỗi `400 COURSE_NOT_READY_FOR_PUBLISH`.

### 4.2 Tiến độ học tập & Resume Playback (BR-12)
1. **Endpoint `PUT /api/progress/lessons/{id}`:**
   - Mobile gửi `watch_position_seconds` lên server mỗi 5–10 giây.
   - Cập nhật vị trí xem dở vào `lesson_progress`.
   - Nếu vị trí xem đạt $\ge 90\%$ thời lượng video: Đánh dấu `is_completed = True` và tự động tính lại phần trăm hoàn thành của toàn khóa học trong bảng `enrollments`.
2. **Endpoint `GET /api/courses/{id}/resume`:** Trả về bài giảng gần nhất và số giây đang xem dở để ứng dụng Android tự động tua tiếp.

### 4.3 Ghi chú gắn mốc thời gian (BR-14)
- **Endpoints CRUD `GET/POST/PUT/DELETE /api/lessons/{id}/notes`:**
- Lưu nội dung ghi chú và mốc thời gian video `timestamp` tính bằng giây.
- Đảm bảo tính riêng tư: Mọi truy vấn bắt buộc có điều kiện `user_id == current_user.id`.

---

## GIAI ĐOẠN 5: Module Ngân Hàng Đề Thi, Quiz & Chấm Điểm Tự Động

### 5.1 Quản lý Ngân hàng câu hỏi & Đề thi (Admin)
- Admin tạo câu hỏi trắc nghiệm / tự luận vào bảng `questions` và các đáp án vào `question_options`.
- Tạo đề thi (`exams`) thuộc một trong hai loại:
  - `in_video_quiz`: Gắn vào bài giảng, có `trigger_timestamp` để video tự dừng và bật pop-up.
  - `end_lesson_exam` / `end_course_exam`: Bài tập củng cố cuối bài hoặc cuối khóa.

### 5.2 Làm bài & Chấm điểm tự động (BR-13)
1. **Lấy đề (`GET /api/quizzes/{id}` hoặc `/api/exams/{id}`):**
   - Trả về danh sách câu hỏi và các lựa chọn đáp án. **Tuyệt đối ẩn trường `is_correct` và `explanation`**.
2. **Nộp bài (`POST /api/exams/{id}/submit`):**
   - Service so sánh các `selected_option_ids` của học viên với đáp án đúng trong DB.
   - Chấm điểm tự động: Tính điểm tổng, kiểm tra đạt/không đạt dựa trên `passing_score`.
   - **Trước khi tạo lượt làm bài mới**, kiểm tra `exercise_attempts` theo bộ `(exam_id, student_id, attempt_number)`; nếu đã đạt `exams.max_attempts` (và `max_attempts <> 0`) thì trả **`403 MAX_ATTEMPTS_REACHED`**. Đây là mã lỗi chính thức theo hợp đồng `08` mục 6.4.
   - Lưu kết quả vào `exercise_attempts` và chi tiết từng câu vào `attempt_answers`.
   - Trả về kết quả cho học viên: Điểm số, đúng/sai từng câu và **bây giờ mới mở phần giải thích (`explanation`)**.

---

## GIAI ĐOẠN 6: Worker Xử Lý Video (FFmpeg HLS) & Phiên Âm (Whisper STT)

### 6.1 Upload video dung lượng lớn (Resumable Upload)
- Hỗ trợ tải lên từng phần (<200MB/chunk, tối đa 5GB/video) theo quyết định `DE-01`.
- Khi các phần tải lên hoàn tất, ghép file và lưu bản gốc vào Cloudflare R2 qua Storage Adapter.
- Tạo bản ghi `videos` ở trạng thái `uploading` $\rightarrow$ `uploaded`, đồng thời khởi tạo 4 bản ghi `pipeline_steps`: `upload`, `transcode`, `transcribe`, `index` ở trạng thái `pending`.

### 6.2 Worker chuyển mã HLS bằng FFmpeg (`workers/video_pipeline.py`)
1. Cập nhật bước `transcode` sang `processing`.
2. Dùng FFmpeg chuyển mã video thô sang chuẩn phát trực tuyến HLS đa độ phân giải (1080p, 720p, 480p, 360p) kèm playlist chính `master.m3u8`.
3. Tải toàn bộ playlist và các file phân đoạn `.ts` lên Cloudflare R2 qua Storage Adapter.
4. Cập nhật `hls_master_url` vào bảng `videos` và đánh dấu bước `transcode` là `completed`.

### 6.3 Worker phiên âm Whisper Speech-to-Text
1. Cập nhật bước `transcribe` sang `processing`.
2. FFmpeg trích xuất âm thanh từ video thành file tạm `audio.wav` (16kHz, mono).
3. Gọi mô hình Whisper **chạy cục bộ** bằng `faster-whisper` trên máy worker: `WHISPER_MODEL_SIZE=small`, `WHISPER_DEVICE=auto`, `WHISPER_COMPUTE_TYPE=int8` khi chạy CPU (không dùng `float16` trên CPU), `WHISPER_LANGUAGE=vi`, `WHISPER_VAD_FILTER=true`. Chạy cục bộ nên **không cần cắt audio thủ công** và không tốn phí theo phút. Lần chạy đầu tiên tải trọng số mô hình (~0.5GB) về máy worker.
4. Nhận kết quả các đoạn phiên âm có `start_time` và `end_time` (sai số $\le \pm 0.5$s theo BR-15).
5. Lưu vào bảng `transcripts` (`version = 1`) và chi tiết từng dòng vào bảng `transcript_segments`.
6. Xóa ngay file `audio.wav` tạm để tiết kiệm đĩa cứng và đánh dấu bước `transcribe` là `completed`.

---

## GIAI ĐOẠN 7: AI Trợ Giảng (RAG Engine), Vector Search & Tóm Tắt

### 7.1 Phân đoạn văn bản (Chunking) & Tạo Embeddings
1. Cập nhật bước `index` sang `processing`.
2. Lấy transcript vừa sinh, gom các dòng phụ đề thành các `chunk` (500 tokens, độ chồng lấp 80–100 tokens theo cấu hình `c1`).
3. Lưu từng đoạn vào `lesson_chunks` với `transcript_version = 1`, `is_active = True`.
4. Gọi mô hình nhúng `text-embedding-3-small` để tạo vector 1536 chiều cho từng chunk.
5. Lưu vector vào bảng `chunk_embeddings` (`embedding_version = 'v1'`).
6. Đánh dấu bước `index` là `completed` và chuyển trạng thái tổng thể video sang `completed`.

### 7.2 Service AI Trợ giảng Hỏi - Đáp (RAG Q&A)
Hiện thực hàm xử lý cho endpoint `POST /api/lessons/{lesson_id}/ask`:
```
1. Kiểm tra quyền ghi danh và hạn mức (max 50 câu/ngày; nếu hết trả 429 AI_QUOTA_EXCEEDED).
2. Tạo vector nhúng cho câu hỏi của học viên (1536 dim).
3. Truy vấn PostgreSQL pgvector:
   - Chỉ tìm kiếm trong bảng lesson_chunks có lesson_id tương ứng và is_active = True.
   - Sắp xếp theo khoảng cách cosine: embedding <=> question_embedding.
   - Áp dụng công thức tăng trọng thời gian tại tài liệu `11` mục 8.2: `d' = d - w * max(0, 1 - |s - t| / W)` với `w = 0.05` (`retrieval_time_weight`) và `W = 120` giây (`retrieval_time_window_seconds`).
     trong đó `s` là mốc bắt đầu của chunk và `t` là vị trí video học viên đang xem, đọc từ `ai_qa_logs.video_position_seconds`. Ngưỡng 0.72 được áp dụng trên khoảng cách gốc `d`, **không** áp dụng trên `d'`.
   - Lấy Top-5 ứng viên và lọc bỏ các chunk có điểm tương đồng < 0.72.
4. Nếu không có chunk nào >= 0.72:
   - **Không gọi mô hình ngôn ngữ.** Trả HTTP 200 kèm `is_out_of_scope = true`, `answer` là câu từ chối cố định theo mẫu ngoài phạm vi bài giảng và `sources` là mảng rỗng (BR-10). Vẫn ghi `ai_qa_logs` và vẫn tính vào hạn mức ngày.
5. Nếu có chunk hợp lệ:
   - Ghép ngữ cảnh các chunk vào System Prompt ép AI chỉ trả lời dựa trên tài liệu bài giảng.
   - Gọi GPT-4o-mini (timeout 30s). Nếu gặp lỗi 429/503/timeout -> tự động fallback sang Gemini Flash.
   - Lưu câu hỏi, câu trả lời, trích dẫn sources vào ai_qa_logs.
   - Trả về câu trả lời kèm danh sách sources (chunk_id, start_time, end_time, text).
```

### 7.3 Tóm tắt bài giảng bằng AI (Auto-Summarize)
- Endpoint `POST /api/lessons/{lesson_id}/summarize`.
- Kiểm tra cache: Truy vấn bảng `ai_summaries` theo `(lesson_id, scope, transcript_version)`. Nếu có và không có cờ `force_regenerate = True`, trả về ngay lập tức (`is_cached = True`).
- Nếu chưa có: Gửi toàn văn transcript vào LLM để tóm tắt thành bullet points và trích xuất các mốc `key_timestamps`. Lưu kết quả vào `ai_summaries` để phục vụ các yêu cầu tiếp theo.

### 7.4 Cơ chế Re-indexing không gián đoạn (Zero-Downtime Re-indexing)
- Khi Admin chỉnh sửa nội dung phụ đề qua màn hình quản trị:
  1. Tăng `version` trong `transcripts` lên $N+1$.
  2. Worker ngầm sinh các chunk mới với `transcript_version = N+1` và đặt `is_active = False`.
  3. Tính toán toàn bộ vector mới trong `chunk_embeddings`.
  4. Sau khi tính toán xong: Chuyển toàn bộ chunk phiên bản cũ sang `is_active = False` và kích hoạt các chunk mới thành `is_active = True`.
  5. Học viên không bị gián đoạn tính năng hỏi đáp trong suốt thời gian hệ thống tính toán lại vector.

---

## GIAI ĐOẠN 8: Tích Hợp Thanh Toán PayOS & Báo Cáo Admin

### 8.1 Luồng thanh toán VietQR qua PayOS (Dự kiến)
1. **Tạo đơn hàng (`POST /api/orders`):**
   - Kiểm tra học viên chưa từng mua khóa học này.
   - Gọi SDK PayOS tạo link thanh toán và mã VietQR.
   - Lưu bản ghi vào bảng `orders` ở trạng thái `pending`, thời hạn `expires_at = now() + 15 phút`.
   - Trả về mã QR và thông tin thanh toán cho Mobile App.
2. **Xử lý Webhook PayOS (`POST /api/webhooks/payos`):**
   - Xác thực chữ ký HMAC từ payload của PayOS.
   - **Xử lý Idempotency:** Kiểm tra mã đơn hàng; nếu đơn đã là `paid`, bỏ qua và trả ngay HTTP 200.
   - **Giao dịch nguyên tử (Atomic Transaction):** Trong cùng một commit DB:
     - Đổi trạng thái đơn hàng sang `paid` và lưu `paid_at`.
     - Tạo bản ghi mới trong bảng `enrollments` cấp quyền học vĩnh viễn cho học viên.
3. **Worker hết hạn đơn hàng (`workers/order_expiry.py`):**
   - Chạy định kỳ (mỗi 1 phút) quét các đơn hàng `pending` có `expires_at < now()` và đổi trạng thái sang `expired` (BR-16).

### 8.2 Dashboard & Báo cáo thống kê Admin
- `GET /api/admin/dashboard`: Tổng hợp số lượng học viên, khóa học, doanh thu và các pipeline video đang xử lý.
- `GET /api/admin/analytics/ai-questions`: Thống kê số lượng câu hỏi AI theo ngày, biểu đồ câu hỏi theo bài giảng, tỷ lệ phản hồi 👍/👎.
- `GET /api/admin/analytics/ai-questions/top`: Trả về danh sách các câu hỏi hay gặp nhất để Admin nắm bắt kiến thức học viên đang vướng mắc.

---

### 8.3 Xác thực chữ ký Webhook PayOS (chi tiết bắt buộc)
- **Thuật toán:** HMAC-SHA256 trên một chuỗi dữ liệu được sắp xếp theo thứ tự bảng chữ cái của tên trường, ghép dạng `key=value` và nối bằng `&`, dùng khóa `PAYOS_CHECKSUM_KEY`; so sánh với trường `signature` trong payload. Khuyến nghị dùng hàm xác thực của SDK `payos` (`verify_payment_webhook`) thay vì tự cài đặt lại.
- **Đọc raw body** trước khi parse JSON; không dựng lại chuỗi chữ ký từ object đã parse vì thứ tự trường và định dạng số có thể lệch.
- **Chống phát lại:** lưu lại `orderCode` kèm mã giao dịch của nhà cung cấp đã xử lý; nếu trùng thì bỏ qua và trả 200.
- **Thứ tự xử lý bắt buộc:** (1) xác thực chữ ký → (2) kiểm tra idempotency → (3) giao dịch nguyên tử đổi đơn sang `paid` và tạo bản ghi `enrollments` → (4) trả HTTP 200. Không gọi dịch vụ ngoài trong lúc mở transaction.
- Chỉ cho phép chuyển `pending` → `paid`. Đơn đã `expired` hoặc `cancelled` thì ghi log và trả 200, không tạo ghi danh.
- Chữ ký sai → trả `401`, ghi log cảnh báo và không tiết lộ chi tiết lỗi ra ngoài.

### 8.4 Seed data cho môi trường phát triển
Script `scripts/seed.py` (idempotent — chạy lại nhiều lần không tạo dữ liệu trùng):
1. Tài khoản quản trị viên bootstrap lấy từ biến môi trường, mật khẩu được băm.
2. 3 danh mục mẫu và 2 khóa học: một khóa miễn phí (test ghi danh miễn phí) và một khóa có phí (test PayOS sandbox).
3. Mỗi khóa có 2 chương, mỗi chương 3 bài giảng; đặt `is_trial_allowed = true` cho ít nhất một bài giảng.
4. Nạp đầy đủ các khóa của `system_settings` theo `DE-09`.
5. Tạo sẵn 1 video kèm transcript, chunk và embedding giả (vector 1536 chiều) để test tính năng RAG mà không cần chạy FFmpeg/Whisper.

Không chạy seed trên môi trường chính thức.

---

## GIAI ĐOẠN 9: Triển Khai & Vận Hành

### 9.1 Mô hình chạy API và Worker
- API (FastAPI/Uvicorn) và Worker là hai tiến trình riêng nhưng cùng trỏ tới Supabase PostgreSQL + pgvector và Cloudflare R2. Trong môi trường phát triển có thể chạy cả hai trên cùng một máy.
- Worker không phục vụ HTTP; nhận việc bằng cách theo dõi bảng `pipeline_steps` (polling cơ sở dữ liệu), khi mở rộng thì chuyển sang hàng đợi Redis.

### 9.2 Công việc định kỳ
- `workers/order_expiry.py`: chạy mỗi 60 giây, quét các đơn `pending` có `expires_at < now()` và chuyển sang `expired` theo BR-16. Khi mở rộng, đưa lên Celery Beat hoặc cron của nền tảng triển khai.
- Dọn phiên và token hết hạn: chạy hằng ngày.
- Xoá chunk và véc-tơ có `is_active = false` quá **7 ngày** kể từ khi bị tắt hiệu lực: chạy hằng ngày.
- Xoá tệp video thô trên R2 quá **30 ngày** kể từ khi bước `transcode` hoàn tất (giữ lại luồng HLS): chạy hằng ngày.
- Thu hồi job mồ côi: quét `pipeline_steps` đang `processing` mà `lease_expires_at < now()` và đưa về `pending` hoặc `failed`: chạy mỗi phút.

### 9.3 Cấu hình và bí mật
- Toàn bộ bí mật đọc từ biến môi trường; tệp `.env` không bao giờ được commit.
- Kết nối Supabase qua connection pooler và đặt giới hạn `pool_size` phù hợp vì hạn mức kết nối của gói miễn phí là hữu hạn.

### 9.4 Quan sát, kiểm tra sức khỏe và quay lui
- `GET /healthz`: kiểm tra ứng dụng còn sống, ping cơ sở dữ liệu và Cloudflare R2; chỉ trả trạng thái, không lộ chi tiết hạ tầng.
- Log JSON có `request_id`, `user_id`, `lesson_id`, độ trễ; không ghi bí mật, OTP gốc hay token gốc.
- Mọi thay đổi lược đồ phải đi qua Alembic; quay lui bằng `alembic downgrade -1`.
- Prometheus và Sentry thuộc phạm vi giai đoạn 2.

---

## BẢNG KIỂM TRA CHẤT LƯỢNG (DEFINITION OF DONE)

Trước khi bàn giao Backend cho đội ngũ Mobile và Web Admin, hệ thống cần thỏa mãn checklist sau:
- [ ] Tất cả 27 bảng và chỉ mục HNSW đã được migrate thành công trên PostgreSQL + pgvector.
- [ ] Swagger UI (`/docs`) hiển thị đầy đủ và chuẩn xác các schema request/response khớp với tài liệu `08`.
- [ ] Mọi response lỗi đều tuân thủ cấu trúc `{ "error": { "code": "...", "message": "..." } }`.
- [ ] Video tải lên được tự động chuyển đổi sang HLS và xem mượt mà trên trình phát video.
- [ ] Whisper phiên âm tiếng Việt chính xác và phụ đề hiển thị khớp timeline video.
- [ ] AI Trợ giảng chỉ trả lời trong ngữ cảnh bài giảng, có trích dẫn timestamp và từ chối khi câu hỏi ngoài phạm vi.
- [ ] Re-indexing khi sửa transcript không làm gián đoạn tính năng chat AI của học viên.
- [ ] Webhook PayOS xử lý idempotent, kích hoạt ghi danh ngay khi nhận thông báo thanh toán thành công.
- [ ] Không tồn tại cấu hình cơ sở dữ liệu hay lưu trữ cục bộ trong repo (không MinIO, không container pgvector); mọi kết nối trỏ tới Supabase và Cloudflare R2.
- [ ] `pytest -q` chạy được; khi chưa khai báo `TEST_DATABASE_URL` thì các test cần cơ sở dữ liệu tự động SKIP thay vì báo lỗi.
