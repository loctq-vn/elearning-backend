# Prompt Chain — Chuỗi Prompt Viết Code Backend Từng Bước Cho Dự Án E-Learning AI

## Cách Dùng Bộ Prompt Này

- Bộ tài liệu gồm **11 bước (Prompt 0 đến Prompt 10)** theo thứ tự nghiêm ngặt: Prompt 0 đồng bộ tooling baseline, sau đó từ hạ tầng, database, module nghiệp vụ cho đến AI pipeline và thanh toán.
- Mỗi prompt đã chứa sẵn **Bối cảnh dự án (Project Context)** và các **Ràng buộc kỹ thuật (Technical Constraints)**, giúp bạn có thể sao chép trực tiếp vào các phiên làm việc AI lập trình (như Antigravity IDE, Cursor, Claude Code...) mà không sợ AI bị lệch hướng hay quên ngữ cảnh.
- Mỗi prompt chỉ định rõ:
  - **Mục tiêu giai đoạn**
  - **Các tệp cần tạo hoặc chỉnh sửa (Target Files)**
  - **Tài liệu tham chiếu đính kèm** (Đặc biệt là `08_FE_BE_Data_Contract.md`, `09_BE_Database_Schema.md`, `10_BE_Architecture.md`, `11_BE_AI_Pipeline_Spec.md`)
  - **Quy chuẩn mã nguồn và tiêu chí kiểm tra (Acceptance Criteria)**.
- Khi hoàn thành từng prompt, hãy chạy test/kiểm tra cú pháp trước khi chuyển sang prompt tiếp theo.

---

## Bối cảnh dự án (COPY sẵn — có trong mọi prompt bên dưới)

```
Dự án: Xây dựng nền tảng học trực tuyến thông minh tích hợp AI Trợ giảng tương tác ngữ cảnh bài giảng.
Kiến trúc Backend: Python FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), PostgreSQL + pgvector, Alembic.
Hạ tầng & Dịch vụ:
- Database: Supabase PostgreSQL + pgvector (cloud chính thức, dùng thống nhất cho mọi môi trường). KHÔNG dùng PostgreSQL cục bộ hay container pgvector.
- Storage: Cloudflare R2 — cloud chính thức duy nhất, dùng cho mọi môi trường. Mọi thao tác đi qua Storage Adapter (SDK boto3 cấu hình tương thích S3). KHÔNG dùng MinIO hay bất kỳ storage cục bộ nào. Không dùng AWS ở giai đoạn hiện tại.
- Xử lý Media: FFmpeg tự chuyển mã HLS đa độ phân giải, Whisper STT phiên âm tiếng Việt.
- AI RAG: OpenAI text-embedding-3-small (1536 dim, cosine similarity), LLM chính GPT-4o-mini, LLM dự phòng Gemini 1.5 Flash.
- Thanh toán: Cổng PayOS (VietQR, xác thực Webhook bằng chữ ký HMAC, xử lý Idempotent).
Nguyên tắc kiến trúc: Clean Layered Architecture (Router -> Middleware/Permissions -> Service -> Repository -> Database/Adapters).
Mọi phản hồi lỗi phải đúng chuẩn: { "error": { "code": "SCREAMING_SNAKE_CASE", "message": "Thông điệp tiếng Việt", "details": null } }.
```

---

## Prompt 0: Đồng Bộ Tooling Baseline & Quy Ước Trước Khi Viết Code

**Mục tiêu:** Bảo đảm mọi phiên làm việc của AI bắt đầu từ cùng một baseline đã có trong repo, thay vì mỗi phiên tự tạo lại cấu hình khác nhau.  
**Tệp cần kiểm tra và đồng bộ:**
- `AGENTS.md` (file luật cho AI agent — nguồn quy ước duy nhất)
- `requirements.txt`, `pyproject.toml` (pin phiên bản + cấu hình ruff/mypy/pytest)
- `.gitignore`, `.env.example`
- `tests/conftest.py`  
**Tài liệu đính kèm:** `AGENTS.md`, `10_BE_Architecture.md`, `12_BE_Implementation_Guide.md`

```text
Bạn là Senior Backend Architect. Trước khi viết bất kỳ dòng code nghiệp vụ nào, hãy đọc AGENTS.md ở thư mục gốc dự án và thực hiện:

1. Xác nhận môi trường chạy là cloud-only: Supabase PostgreSQL + pgvector và Cloudflare R2 dùng thống nhất cho mọi môi trường (dev/test/prod).
   Không tạo Dockerfile/docker-compose để chạy PostgreSQL hay storage cục bộ; không cấu hình MinIO.
2. Kiểm tra requirements.txt đã pin đủ thư viện (fastapi, uvicorn[standard], pydantic[email], pydantic-settings,
   sqlalchemy[asyncio], asyncpg, psycopg2-binary, alembic, pgvector, python-jose[cryptography], passlib[bcrypt],
   python-multipart, httpx, aiofiles, boto3, payos, pytest, pytest-asyncio, ruff, mypy) và bổ sung nếu thiếu.
3. Kiểm tra .env.example có đủ DATABASE_URL, DATABASE_URL_SYNC, TEST_DATABASE_URL, TEST_DATABASE_URL_SYNC,
   STORAGE_*, AI_*, PAYOS_*, SMTP_*, CORS_ORIGINS.
4. Chạy ruff check và mypy trên khung dự án để xác nhận cấu hình trong pyproject.toml hoạt động.

Tiêu chí nghiệm thu: `pip install -r requirements.txt`, `ruff check .` và `pytest -q` đều chạy được;
khi chưa khai báo TEST_DATABASE_URL thì các test cần database tự động SKIP thay vì báo lỗi.
```

---

## Prompt 1: Khởi Tạo Dự Án, Cấu Hình Core & Trình Xử Lý Lỗi Tập Trung

**Mục tiêu:** Thiết lập cấu trúc thư mục phân tầng, Pydantic Settings, CORS, logging và Error Handler toàn cục chuẩn theo Hợp đồng dữ liệu 08.  
**Tệp đầu ra cần tạo:**
- `app/core/config.py`
- `app/core/errors.py`
- `app/core/security.py`
- `app/main.py`
- `requirements.txt` / `pyproject.toml`
- `.env.example`  
**Tài liệu đính kèm:** `10_BE_Architecture.md`, `08_FE_BE_Data_Contract.md` (Mục Quy ước tài liệu & Phụ lục A)

```text
Bạn là Senior Backend Architect. Hãy khởi tạo dự án FastAPI cho nền tảng E-Learning AI dựa trên [Bối cảnh dự án] và tài liệu 10_BE_Architecture.md:

1. Tạo tệp requirements.txt gồm các thư viện tương thích:
   fastapi, uvicorn[standard], pydantic[email], pydantic-settings, sqlalchemy[asyncio], asyncpg, psycopg2-binary, alembic, pgvector, python-jose[cryptography], passlib[bcrypt], python-multipart, httpx, aiofiles, boto3, payos.

2. Tạo app/core/config.py:
   - Dùng pydantic_settings.BaseSettings đọc các biến môi trường từ .env (DATABASE_URL, SECRET_KEY, ACCESS_TOKEN_EXPIRE_SECONDS=900, REFRESH_TOKEN_EXPIRE_DAYS=7, STORAGE_*, AI_*, PAYOS_*, SMTP_*).

3. Tạo app/core/errors.py:
   - Định nghĩa lớp AppException kế thừa Exception lưu trữ http_code, error_code (SCREAMING_SNAKE_CASE) và message tiếng Việt.
   - Viết các Exception Handler đăng ký với FastAPI:
     + Handler cho AppException: Trả về JSON { "error": { "code": exc.error_code, "message": exc.message, "details": exc.details } }.
     + Handler cho RequestValidationError của Pydantic: Trả về HTTP 400 với error.code = "VALIDATION_ERROR" và chi tiết trường lỗi trong error.details.
     + Handler cho Exception chung không kiểm soát: Trả về HTTP 500 với error.code = "INTERNAL_ERROR" và message "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.".

4. Tạo app/core/security.py:
   - Hàm băm và kiểm tra mật khẩu bằng passlib (bcrypt).
   - Hàm tạo JWT Access Token (hạn 900s) và Refresh Token.
   - Hàm giải mã JWT và kiểm tra hạn ngạch.

5. Tạo app/main.py:
   - Khởi tạo FastAPI application với OpenAPI documentation (/docs).
   - Cấu hình CORS middleware cho phép các domain Web Admin và Mobile App kết nối.
   - Đăng ký toàn bộ error handler từ errors.py.
   - Thêm endpoint kiểm tra sức khỏe GET /health trả về status "ok" và timestamp hiện tại.

Hãy xuất toàn bộ code chi tiết, có chú thích rõ ràng và tuân thủ typing chuẩn Python.
```

---

## Prompt 2: Viết Models SQLAlchemy 2.0 & Di Trú Alembic Cho 27 Bảng

**Mục tiêu:** Hiện thực toàn bộ 27 bảng dữ liệu, ràng buộc quan hệ, kiểu Vector 1536 chiều và script di trú Alembic có HNSW index.  
**Tệp đầu ra cần tạo:**
- `app/db/base.py`
- `app/db/session.py`
- `app/db/models/user.py`
- `app/db/models/course.py`
- `app/db/models/video.py`
- `app/db/models/ai_knowledge.py`
- `app/db/models/learning.py`
- `app/db/models/exam.py`
- `app/db/models/commerce_ops.py`
- `alembic/versions/xxxx_initial_schema.py`
- `scripts/seed_data.py`  
**Tài liệu đính kèm:** `09_BE_Database_Schema.md`

```text
Bạn là Database Specialist & SQLAlchemy 2.0 Expert. Dựa trên tài liệu đặc tả 09_BE_Database_Schema.md, hãy xây dựng toàn bộ tầng CSDL cho hệ thống:

1. Tạo app/db/session.py:
   - Cấu hình AsyncEngine và async_sessionmaker dùng asyncpg.
   - Viết async generator get_db() cung cấp AsyncSession cho FastAPI Depends.

2. Định nghĩa các Model SQLAlchemy (sử dụng DeclarativeBase và Mapped[] kiểu mới của SQLAlchemy 2.0) cho đầy đủ 27 bảng trong thư mục app/db/models/:
   - user.py: users, otp_codes, refresh_tokens.
   - course.py: categories, courses, chapters, lessons.
   - video.py: videos, pipeline_steps, transcripts, transcript_segments.
   - ai_knowledge.py: lesson_chunks, chunk_embeddings (dùng pgvector.sqlalchemy.Vector(1536)).
   - learning.py: enrollments, lesson_progress, notes.
   - exam.py: questions, question_options, exams, exam_questions, exercise_attempts, attempt_answers.
   - commerce_ops.py: orders, ai_qa_logs, ai_summaries, notifications, system_settings.

3. Đảm bảo 100% các ràng buộc kỹ thuật đã nêu trong tài liệu 09:
   - Toàn bộ PK là UUID (uuid_generate_v4() hoặc Python uuid.uuid4).
   - Bảng lesson_chunks có composite unique constraint: (lesson_id, transcript_version, chunk_config_version, chunk_index).
   - Foreign keys có đầy đủ ondelete="CASCADE" hoặc "SET NULL" theo đúng tài liệu.
   - Khai báo đúng các Enums: user_role, course_status, video_overall_status, pipeline_step, step_status, order_status, question_type, exam_type, ai_feedback...

4. Cấu hình Alembic & Viết Migration Script:
   - Đảm bảo script migration đầu tiên thực thi lệnh SQL: CREATE EXTENSION IF NOT EXISTS vector;
   - Tạo index HNSW trên bảng chunk_embeddings:
     CREATE INDEX ix_emb_v1 ON chunk_embeddings USING hnsw (embedding vector_cosine_ops) WHERE embedding_version = 'v1';
   - Tạo unique index case-insensitive cho email: CREATE UNIQUE INDEX uq_users_email ON users (LOWER(email));

5. Viết script scripts/seed_data.py:
   - Nạp tài khoản Admin mặc định (mật khẩu đã băm).
   - Nạp các danh mục khóa học mẫu.
   - Nạp các giá trị mặc định cho bảng system_settings (embedding_version='v1', top_k=5, threshold=0.72, time_weight_window=120, daily_qa_limit=50).

Hãy cung cấp mã nguồn hoàn chỉnh cho các file trên.
```

---

## Prompt 3: Module Xác Thực (Auth), OTP & Middleware Phân Quyền

**Mục tiêu:** Hoàn thành luồng đăng ký, xác thực OTP email, đăng nhập JWT, xoay vòng refresh token và middleware phân quyền học viên/admin/ghi danh.  
**Tệp đầu ra cần tạo:**
- `app/modules/auth/schemas.py`
- `app/modules/auth/repository.py`
- `app/modules/auth/service.py`
- `app/modules/auth/router.py`
- `app/core/permissions.py`
- `app/adapters/mailer.py`  
**Tài liệu đính kèm:** `08_FE_BE_Data_Contract.md` (Mục 1: Authentication), `09_BE_Database_Schema.md` (Bảng users, otp_codes, refresh_tokens)

```text
Bạn là Backend Security Engineer. Dựa trên Mục 1 của 08_FE_BE_Data_Contract.md và các quy tắc BR-01, BR-02, BR-03 trong 00_SYSTEM_BUSINESS_ANALYSIS.md, hãy lập trình module Auth:

1. Tạo app/adapters/mailer.py:
   - Dịch vụ gửi email bất đồng bộ (qua SMTP hoặc API Resend) để gửi mã OTP 6 chữ số có giao diện email HTML chuyên nghiệp.

2. Tạo app/modules/auth/schemas.py:
   - Request & Response Pydantic models khớp 100% với hợp đồng dữ liệu:
     + RegisterRequest (full_name regex chữ cái tiếng Việt, email, password >= 8 ký tự kèm chữ hoa/thường/số/ký tự đặc biệt).
     + VerifyOtpRequest (email, otp_code 6 số, purpose enum 'registration' | 'password_reset').
     + LoginRequest (email, password).
     + RefreshTokenRequest, ForgotPasswordRequest, ResetPasswordRequest.
     + TokenResponse, AuthMessageResponse.

3. Tạo app/modules/auth/repository.py & service.py:
   - Luồng Đăng ký: Kiểm tra email tồn tại (trả 409 EMAIL_ALREADY_EXISTS). Sinh mã OTP 6 số, băm lưu vào otp_codes (hạn 300s). Gửi mail qua mailer adapter.
   - Luồng Verify OTP: Kiểm tra mã OTP, kiểm tra số lần thử sai (< 5 lần, nếu quá 5 lần khóa 15 phút). Nếu purpose == 'registration' -> chuyển is_verified = True, tạo user, sinh token và tự động đăng nhập. Nếu purpose == 'password_reset' -> trả về reset_token.
   - Luồng Đăng nhập: Kiểm tra tài khoản bị khóa (is_locked) và đã xác minh (is_verified). Thu hồi các refresh token cũ (nguyên tắc 1 thiết bị cho học viên). Cấp access_token (900s) và refresh_token mới (7 ngày).
   - Luồng Refresh: Xoay vòng (rotate) refresh token, thu hồi token cũ, cấp cặp token mới.

4. Tạo app/core/permissions.py:
   - Dependency get_current_user: Xác thực JWT Bearer, kiểm tra tài khoản còn hoạt động.
   - Dependency require_admin: Kiểm tra role == 'admin', nếu sai ném 403 FORBIDDEN.
   - Dependency require_enrolled(lesson_id): Kiểm tra xem bài giảng có cho phép học thử (is_trial_allowed) hay không; nếu không, kiểm tra học viên đã ghi danh (bảng enrollments) hay chưa, nếu chưa ném 403 NOT_ENROLLED.

5. Tạo app/modules/auth/router.py:
   - Khai báo đầy đủ các endpoints: POST /api/auth/register, /verify-otp, /resend-otp, /login, /refresh, /logout, /forgot-password, /reset-password.
   - Gắn router vào FastAPI app trong main.py.

Hãy viết code chuẩn Async SQLAlchemy, validate dữ liệu nghiêm ngặt và xử lý mã lỗi chính xác.
```

---

## Prompt 4: Module Khóa Học, Bài Giảng, Tiến Độ Học & Ghi Chú Video

**Mục tiêu:** Xây dựng tính năng duyệt khóa học, quản lý cây chương - bài giảng, kiểm duyệt xuất bản (BR-06), lưu tiến độ xem video dở (BR-12) và ghi chú theo timestamp (BR-14).  
**Tệp đầu ra cần tạo:**
- `app/modules/courses/` (schemas, repository, service, router)
- `app/modules/lessons/` (schemas, repository, service, router)
- `app/modules/progress/` (schemas, repository, service, router)
- `app/modules/notes/` (schemas, repository, service, router)  
**Tài liệu đính kèm:** `08_FE_BE_Data_Contract.md` (Mục 2: Khóa học, Mục 3: Tiến độ, Mục 7: Ghi chú)

```text
Bạn là Senior Backend Developer. Dựa trên Mục 2, Mục 3 và Mục 7 của 08_FE_BE_Data_Contract.md, hãy lập trình các module Khóa học, Bài giảng, Tiến độ và Ghi chú:

1. Module Courses & Lessons:
   - Schemas: Khai báo Pydantic schemas cho Khóa học, Chương, Bài giảng (hỗ trợ tạo mới, cập nhật, chi tiết kèm danh sách chương/bài).
   - Service Khóa học:
     + Học viên: GET /api/courses chỉ xem các khóa có status = 'published'. Hỗ trợ lọc theo category, tìm kiếm keyword, phân trang chuẩn { data, total, page, page_size, total_pages }.
     + Admin: Đầy đủ CRUD khóa học, chương và bài giảng.
     + Quy tắc xuất bản khóa học (BR-06): Khi Admin chuyển status sang 'published', Service bắt buộc kiểm tra khóa học phải có ít nhất 1 chương và tất cả bài giảng bên trong đều có video ở trạng thái 'completed'. Nếu không đạt trả 400 COURSE_NOT_READY_FOR_PUBLISH.
   - Service Bài giảng:
     + GET /api/lessons/{id}: Yêu cầu permission require_enrolled. Trả về thông tin bài học, hls_master_url, danh sách phụ đề và vị trí xem dở gần nhất của học viên.

2. Module Progress (Tiến độ học tập & Tiếp tục học):
   - Endpoint PUT /api/progress/lessons/{id}:
     + Nhận watch_position_seconds từ Mobile App.
     + Lưu/cập nhật vào bảng lesson_progress.
     + Nếu watch_position_seconds >= 90% thời lượng video: Đánh dấu is_completed = True, completed_at = now().
     + Tính lại progress_percent của cả khóa học trong bảng enrollments.
   - Endpoint GET /api/courses/{id}/resume: Trả về bài giảng gần nhất đang học dở và số giây để client tự động tua tiếp (BR-12).

3. Module Notes (Ghi chú gắn mốc thời gian video - BR-14):
   - Endpoints: GET/POST /api/lessons/{id}/notes, PUT/DELETE /api/notes/{id}.
   - Ràng buộc: Mọi thao tác đều phải lọc theo user_id = current_user.id để bảo vệ tính riêng tư của học viên. Nội dung từ 1-2000 ký tự, timestamp >= 0 tính bằng giây.

Hãy xuất toàn bộ code sạch, tuân thủ kiến trúc phân tầng router -> service -> repository.
```

---

## Prompt 5: Module Ngân Hàng Đề Thi, Quiz Giữa Video & Bài Tập Đánh Giá

**Mục tiêu:** Xây dựng hệ thống ngân hàng câu hỏi, tạo đề thi (quiz xen kẽ video có trigger timestamp & bài tập cuối khóa), chấm điểm trắc nghiệm tự động và quản lý số lần làm bài (BR-13).  
**Tệp đầu ra cần tạo:**
- `app/modules/exams/schemas.py`
- `app/modules/exams/repository.py`
- `app/modules/exams/service.py`
- `app/modules/exams/router.py`  
**Tài liệu đính kèm:** `08_FE_BE_Data_Contract.md` (Mục 6: Quiz & Bài tập), `09_BE_Database_Schema.md` (Nhóm bảng exam)

```text
Bạn là Backend Engineer phụ trách module Khảo thí (Exams & Quizzes). Dựa trên Mục 6 của 08_FE_BE_Data_Contract.md và quy tắc BR-13 trong 00_SYSTEM_BUSINESS_ANALYSIS.md, hãy lập trình module Đề thi và Bài tập:

1. Schemas:
   - QuestionCreate/Update: nội dung, loại câu hỏi (single_choice, multiple_choice, true_false, essay), độ khó, danh sách phương án options (nội dung, is_correct), lời giải thích explanation.
   - ExamCreate/Update: tiêu đề, exam_type (in_video_quiz, end_lesson_exam, end_course_exam), duration_minutes, passing_score, max_attempts, danh sách câu hỏi kèm điểm số và trigger_timestamp (nếu là in_video_quiz).
   - ExamTakeResponse: cấu trúc đề thi trả về cho học viên làm bài (TUYỆT ĐỐI KHÔNG chứa trường is_correct và explanation).
   - SubmitExamRequest: danh sách câu trả lời của học viên ({ question_id, selected_option_ids, essay_answer }).
   - ExamResultResponse: điểm số đạt được, kết quả đúng/sai từng câu, đánh giá đạt/không đạt và lời giải thích chi tiết.

2. Repository & Service:
   - Quản trị viên: Đầy đủ CRUD ngân hàng câu hỏi và tạo đề thi. Cho phép gán quiz vào bài giảng kèm mốc thời gian xuất hiện trong video.
   - Học viên:
     + Lấy đề quiz/bài tập: Kiểm tra quyền ghi danh. Kiểm tra giới hạn số lần làm bài (max_attempts), nếu vượt quá ném lỗi 403 MAX_ATTEMPTS_REACHED (mã lỗi chính thức theo hợp đồng 08 mục 6.4). Tạo bản ghi exercise_attempts ở trạng thái 'in_progress'.
     + Nộp bài (Submit):
       * So sánh selected_option_ids của học viên với question_options có is_correct = True.
       * Chấm điểm tự động tức thì cho các câu trắc nghiệm, tính tổng điểm đạt được và tỷ lệ phần trăm.
       * Xác định is_passed = (total_score >= passing_score).
       * Lưu chi tiết câu trả lời vào attempt_answers và cập nhật exercise_attempts sang 'graded'.
       * Trả về kết quả chấm điểm kèm explanation của từng câu hỏi cho học viên.

3. Router:
   - Khai báo đầy đủ các route cho cả Học viên (lấy đề, nộp bài, xem lịch sử làm bài) và Admin (quản lý câu hỏi, gán đề thi).

Hãy viết code chi tiết, chú ý tính toán điểm số chính xác và kiểm tra chặt chẽ quyền sở hữu bài thi.
```

---

## Prompt 6: Bộ Điều Hợp Lưu Trữ (Cloudflare R2) & Worker Xử Lý Video (FFmpeg + Whisper)

**Mục tiêu:** Xây dựng cơ chế tải lên video lớn (resumable chunked upload < 200MB, max 5GB), worker FFmpeg chuyển mã HLS đa độ phân giải và Whisper phiên âm tiếng Việt (BR-07, BR-15).  
**Tệp đầu ra cần tạo:**
- `app/adapters/storage.py`
- `app/adapters/ai/whisper.py`
- `app/workers/video_pipeline.py`
- `app/modules/videos/router.py`, `service.py`, `schemas.py`  
**Tài liệu đính kèm:** `11_BE_AI_Pipeline_Spec.md` (Mục 3, 4, 5), `08_FE_BE_Data_Contract.md` (Mục 9: Upload & Pipeline)

```text
Bạn là Media & Pipeline Engineer. Dựa trên tài liệu 11_BE_AI_Pipeline_Spec.md (Mục 3, 4, 5) và các quyết định DE-01, DE-02, DE-04, hãy lập trình hệ thống xử lý video bài giảng:

1. Tạo app/adapters/storage.py:
   - Định nghĩa interface StorageAdapter (abstract class) với các phương thức: upload_file, upload_directory (cho thư mục HLS chứa m3u8 và ts), get_signed_url, delete_file.
   - Hiện thực R2StorageAdapter dùng boto3 cấu hình tương thích S3 kết nối Cloudflare R2 (biến STORAGE_*), dùng cho mọi môi trường. Service/worker không gọi boto3 trực tiếp, chỉ gọi qua Storage Adapter — thiết kế tổng quát để sau này thay bằng AWS S3 (hướng migration tương lai) mà không sửa business logic.

2. Tạo app/adapters/ai/whisper.py:
   - Client gọi mô hình Whisper CHẠY CỤC BỘ qua AI Adapter bằng thư viện faster-whisper: model 'small', device 'auto', compute_type 'int8' khi chạy CPU (KHÔNG dùng float16 trên CPU), beam_size 5, vad_filter=True, language='vi'. Không cần cắt audio thủ công vì không có giới hạn dung lượng như khi gọi API.
   - Trả về danh sách các đoạn phiên âm gồm start_time (float), end_time (float), text (string). Đảm bảo sai số timestamp <= 0.5s theo quy tắc BR-15.

3. Tạo app/workers/video_pipeline.py:
   - Hàm process_video_pipeline(video_id: str): Chạy bất đồng bộ (FastAPI BackgroundTasks hoặc Celery task).
   - Bước 1 (transcode):
     + Cập nhật pipeline_steps (step='transcode', status='processing').
     + Dùng FFmpeg (subprocess hoặc ffmpeg-python) chuyển mã video thô thành chuẩn HLS đa biến thể (1080p, 720p, 480p) kèm file master.m3u8 và các file .ts.
     + Upload toàn bộ thư mục HLS lên Cloudflare R2 (qua Storage Adapter).
     + Cập nhật hls_master_url trong bảng videos. Đánh dấu step 'transcode' completed.
   - Bước 2 (transcribe):
     + Cập nhật pipeline_steps (step='transcribe', status='processing').
     + Trích xuất âm thanh từ video thành file tạm audio.wav (16kHz, mono).
     + Gọi whisper.py để nhận toàn văn phụ đề và các segments.
     + Lưu bản ghi transcripts (version=1, language='vi') và các transcript_segments vào DB.
     + Xóa ngay file audio.wav tạm để giải phóng bộ nhớ. Đánh dấu step 'transcribe' completed.
   - Quản lý lỗi & Retry:
     + Nếu bất kỳ bước nào lỗi: cập nhật attempt_count và next_attempt_at theo backoff 30 giây, 2 phút, 10 phút; sau 3 lần thất bại thì đặt status='failed' cho bước đó và overall_status='failed' cho bảng videos, lưu error_message chi tiết để Admin kích hoạt chạy lại (Retry). Khi chạy lại bước transcode phải xoá thư mục HLS dở trước khi ghi mới.

4. Tạo app/modules/videos/ (schemas, service, router):
   - Endpoint POST /api/admin/videos/upload: Nhận video (hỗ trợ multipart chunked upload theo DE-01), tạo bản ghi video và 4 bước pipeline ở trạng thái 'pending', kích hoạt background worker.
   - Endpoint GET /api/admin/videos/{id}/pipeline-status: Trả về trạng thái tổng thể và tiến trình chi tiết của 4 bước: upload, transcode, transcribe (stt), index.
   - Endpoint POST /api/admin/videos/{id}/pipeline/retry: Cho phép chạy lại bước pipeline bị lỗi.

Hãy viết code xử lý file an toàn, dọn dẹp file rác trong khối finally và ghi log đầy đủ.

Tiêu chí nghiệm thu bổ sung: mọi thao tác lưu trữ đều đi qua Storage Adapter (app/adapters/storage.py), không import boto3 trong service/worker; pipeline không tham chiếu AWS và chỉ dùng Cloudflare R2 cho mọi môi trường (không MinIO, không storage cục bộ).
```

---

## Prompt 7: AI RAG Q&A Engine, Vector Search & Tóm Tắt Bài Giảng

**Mục tiêu:** Hoàn thiện khâu tạo chunking văn bản, pgvector embedding, tìm kiếm ngữ nghĩa Top-5 với tăng trọng thời gian (time-weighting), RAG Q&A với Fallback Model và Tóm tắt bài giảng có cache (BR-08, BR-10, BR-11).  
**Tệp đầu ra cần tạo:**
- `app/adapters/ai/embeddings.py`
- `app/adapters/ai/llm.py`
- `app/adapters/ai/prompts/rag_tutor.py`
- `app/workers/reindex.py`
- `app/modules/ai/` (schemas, repository, service, router)  
**Tài liệu đính kèm:** `11_BE_AI_Pipeline_Spec.md` (Mục 6, 7, 8, 9, 10, 11), `08_FE_BE_Data_Contract.md` (Mục 4: AI Q&A, Mục 5: Tóm tắt)

```text
Bạn là AI Engineer & RAG Specialist. Dựa trên tài liệu 11_BE_AI_Pipeline_Spec.md và Mục 4, Mục 5 của 08_FE_BE_Data_Contract.md, hãy lập trình toàn bộ tầng AI cho Backend:

1. Tạo app/adapters/ai/:
   - embeddings.py: Gọi OpenAI text-embedding-3-small tạo vector 1536 chiều, chuẩn hóa vector cho cosine distance.
   - llm.py: Wrapper gọi LLM với chính sách: thử gọi GPT-4o-mini (timeout 30s); nếu timeout hoặc lỗi quá tải (HTTP 429, 503) thì tự động gọi mô hình dự phòng Gemini 1.5 Flash đúng 1 lần. Tổng thời gian không quá 60s.
   - prompts/rag_tutor.py: System Prompt chuyên biệt ép mô hình chỉ trả lời dựa vào ngữ cảnh transcript được cung cấp (In-context boundary - BR-10), luôn trích dẫn nguồn, từ chối trả lời nếu câu hỏi nằm ngoài nội dung bài học.

2. Hoàn thành bước thứ 4 của Video Pipeline (Indexing) trong app/workers/video_pipeline.py & reindex.py:
   - Thuật toán Chunking: Gom các transcript_segments thành các đoạn ~500 tokens, độ chồng lấp 80-100 tokens (cấu hình c1). Lưu vào lesson_chunks kèm start_time, end_time và transcript_version.
   - Vector Indexing: Sinh embedding cho từng chunk, lưu vào chunk_embeddings (embedding_version='v1').
   - Đánh dấu pipeline step 'index' và video overall_status là 'completed'.

3. Service AI Trợ giảng Hỏi - Đáp (RAG Q&A):
   - Endpoint POST /api/lessons/{lesson_id}/ask:
     + Kiểm tra hạn ngạch: Kiểm tra số câu đã hỏi hôm nay của học viên trong ai_qa_logs (max 50 câu/ngày; nếu vượt ném 429 AI_QUOTA_EXCEEDED).
     + Sinh embedding câu hỏi (1536 dim).
     + Truy vấn pgvector trong lesson_chunks có lesson_id tương ứng và is_active = True:
       * Sắp xếp theo khoảng cách hiệu dụng d' = d - w * max(0, 1 - |s - t| / W) với w = 0.05 và W = 120 giây; s là start_time của chunk, t là vị trí video học viên đang xem (đọc từ ai_qa_logs.video_position_seconds). Ngưỡng 0.72 áp dụng trên khoảng cách gốc d, KHÔNG áp dụng trên d'.
       * Lấy Top-5 chunk có similarity >= 0.72.
     + Nếu không có chunk nào >= 0.72: KHÔNG gọi mô hình ngôn ngữ. Trả HTTP 200 kèm is_out_of_scope=true, answer là câu từ chối cố định theo mẫu ngoài phạm vi và sources là mảng rỗng (BR-10). Vẫn ghi ai_qa_logs và vẫn tính vào hạn mức ngày.
     + Nếu có chunk: Ghép ngữ cảnh vào Prompt, gọi LLM, lưu vào ai_qa_logs, trả về câu trả lời kèm mảng sources (chunk_id, text, start_time, end_time, relevance_score).
   - Endpoint GET /api/lessons/{lesson_id}/chat-history: Lấy lịch sử hỏi đáp.
   - Endpoint POST /api/ai-messages/{message_id}/feedback: Ghi nhận đánh giá 👍/👎 (up/down).

4. Service AI Tóm tắt bài giảng (Auto-Summarize - BR-11):
   - Endpoint POST /api/lessons/{lesson_id}/summarize:
     + Kiểm tra bảng ai_summaries theo (lesson_id, scope, transcript_version). Nếu đã có và force_regenerate = False -> trả về bản tóm tắt từ cache (is_cached = True).
     + Nếu chưa có: Kiểm tra độ dài transcript (nếu < 100 từ trả 400 TRANSCRIPT_TOO_SHORT). Gọi LLM tóm tắt dạng bullet points và trích xuất key_timestamps. Lưu vào ai_summaries và trả về client.

5. Cơ chế Zero-Downtime Re-indexing (BR-08, DE-07):
   - Khi Admin sửa phụ đề transcript: tăng transcript_version = N+1. Worker tính toán chunk và vector mới với is_active = False. Khi xong mới lật cờ is_active = True để không làm gián đoạn học viên đang học.

Hãy viết code tối ưu truy vấn SQL với pgvector, bảo đảm prompt bảo mật chống prompt injection.
```

---

## Prompt 8: Tích Hợp Cổng Thanh Toán PayOS & Webhook Xử Lý Idempotent

**Mục tiêu:** Xây dựng quy trình thanh toán VietQR qua PayOS, tạo đơn hàng 15 phút, xác thực Webhook bằng chữ ký HMAC bảo đảm tính Idempotent và nguyên tử (Atomic Transaction) (BR-05, BR-16).  
**Tệp đầu ra cần tạo:**
- `app/adapters/payos.py`
- `app/workers/order_expiry.py`
- `app/modules/orders/` (schemas, repository, service, router)  
**Tài liệu đính kèm:** `08_FE_BE_Data_Contract.md` (Mục 8: Thanh toán PayOS), `10_BE_Architecture.md` (Mục 8.4: Tích hợp thanh toán)

```text
Bạn là Payment Integration Specialist. Dựa trên Mục 8 của 08_FE_BE_Data_Contract.md và các quy tắc BR-05, BR-16 trong 00_SYSTEM_BUSINESS_ANALYSIS.md, hãy lập trình module Thanh toán PayOS:

1. Tạo app/adapters/payos.py:
   - Khởi tạo PayOS client với PAYOS_CLIENT_ID, PAYOS_API_KEY, PAYOS_CHECKSUM_KEY.
   - Hàm create_payment_link(order_code, amount, description, return_url, cancel_url): Gọi PayOS tạo link thanh toán và mã VietQR.
   - Hàm verify_webhook_data(webhook_body, signature): Xác thực tính toàn vẹn của dữ liệu webhook bằng chữ ký HMAC SHA256.

2. Tạo app/modules/orders/ (schemas, repository, service, router):
   - Endpoint POST /api/orders:
     + Học viên chọn mua khóa học. Kiểm tra chưa ghi danh (nếu đã mua trả 409 ALREADY_ENROLLED).
     + Tạo mã order_code số nguyên duy nhất.
     + Gọi PayOS adapter tạo link thanh toán.
     + Lưu bản ghi vào bảng orders (status='pending', expires_at = now() + 15 phút).
     + Trả về thông tin đơn hàng, qr_code_url và payment_url cho Mobile App.
   - Endpoint GET /api/orders/{order_code}/status: Cho phép Mobile App polling trạng thái đơn hàng (mỗi 3 giây).
   - Endpoint POST /api/webhooks/payos (Xử lý Webhook PayOS):
     + KHÔNG dùng middleware JWT cho endpoint này.
     + Xác thực chữ ký HMAC từ payload.
     + XỬ LÝ IDEMPOTENCY: Kiểm tra trạng thái đơn hàng trong DB; nếu đơn hàng đã ở trạng thái 'paid', lập tức trả về HTTP 200 { "status": "success", "message": "Order already processed" } mà không thực hiện lại logic ghi danh.
     + GIAO DỊCH NGUYÊN TỬ (Atomic Transaction): Nếu đơn hàng đang 'pending':
       * Cập nhật orders: status = 'paid', paid_at = now(), transaction_id = provider_transaction_id.
       * Tạo bản ghi mới trong enrollments: cấp quyền học vĩnh viễn khóa học cho học viên đó.
       * Cả hai thao tác phải commit trong cùng một database transaction.

3. Tạo app/workers/order_expiry.py (BR-16):
   - Tác vụ nền chạy định kỳ (mỗi 1 phút): Quét các đơn hàng trong bảng orders có status = 'pending' và expires_at < now() -> Cập nhật status = 'expired' để hủy đơn và giải phóng tài nguyên.

Hãy chú ý xử lý chặt chẽ concurrency, tránh race condition khi webhook đến cùng lúc với request polling.
```

---

## Prompt 9: Module Báo Cáo Thống Kê Admin & Phân Tích Hành Vi AI

**Mục tiêu:** Cung cấp các API tổng hợp số liệu cho Dashboard Admin, báo cáo doanh thu và thống kê mức độ tương tác câu hỏi AI.  
**Tệp đầu ra cần tạo:**
- `app/modules/analytics/schemas.py`
- `app/modules/analytics/service.py`
- `app/modules/analytics/router.py`  
**Tài liệu đính kèm:** `08_FE_BE_Data_Contract.md` (Mục 12: Báo cáo & Thống kê Admin)

```text
Bạn là Data Analyst & Backend Developer. Dựa trên Mục 12 của 08_FE_BE_Data_Contract.md, hãy lập trình module Báo cáo & Phân tích dành riêng cho Quản trị viên (yêu cầu quyền require_admin):

1. Endpoint GET /api/admin/dashboard:
   - Tổng hợp các chỉ số nhanh: tổng số học viên, tổng số khóa học đã xuất bản, tổng doanh thu thực tế, số video đang xử lý trong pipeline.

2. Endpoint GET /api/admin/revenue/summary & /chart & /transactions:
   - Lọc theo khoảng thời gian date_from, date_to.
   - Tổng doanh thu (VND), số giao dịch thành công/thất bại, biểu đồ doanh thu theo ngày/tháng, danh sách chi tiết các đơn hàng kèm tên học viên và khóa học.

3. Endpoint GET /api/admin/analytics/ai-questions (Thống kê AI - Màn hình A-14):
   - Thống kê: tổng số câu hỏi AI, số câu hỏi hôm nay, thời gian phản hồi trung bình (avg_response_time), tỷ lệ hài lòng (% đánh giá 👍 từ ai_qa_logs).
   - Biểu đồ số lượng câu hỏi theo ngày (daily_chart) và biểu đồ phân bổ câu hỏi theo từng bài giảng (by_lesson_chart) để Admin biết bài giảng nào học viên đang gặp nhiều khó khăn.

4. Endpoint GET /api/admin/analytics/ai-questions/top:
   - Trả về danh sách các câu hỏi phổ biến nhất kèm số lần hỏi tương tự (ask_count), số lượt thumbs_up, thumbs_down và các đoạn transcript hay được trích dẫn nhất.

5. Endpoint GET /api/admin/analytics/students:
   - Tổng hợp tỷ lệ hoàn thành khóa học (completion_rate) từ bảng enrollments và lesson_progress.
   - Danh sách các bài giảng có tỷ lệ học viên bỏ dở cao (high_dropout_lessons).

Hãy viết các câu truy vấn SQLAlchemy / SQL thuần tối ưu (GROUP BY, COUNT, AVG), tránh n+1 query problem.
```

---

## Prompt 10: Viết Bộ Kiểm Thử Tự Động (Integration Tests) & Kiểm Tra Nghiệp Vụ

**Mục tiêu:** Xây dựng bộ test suite tự động hoàn chỉnh bằng `pytest` và `httpx` để kiểm tra toàn diện 100% các luồng API từ Auth, Course, RAG AI đến Webhook.  
**Tệp đầu ra cần tạo:**
- `tests/conftest.py`
- `tests/test_auth.py`
- `tests/test_courses.py`
- `tests/test_ai_rag.py`
- `tests/test_payments.py`
- `scripts/run_tests.sh`  
**Tài liệu đính kèm:** `08_FE_BE_Data_Contract.md`, `12_BE_Implementation_Guide.md`

```text
Bạn là Senior QA Automation Engineer. Dựa trên 08_FE_BE_Data_Contract.md và checklist Definition of Done trong 12_BE_Implementation_Guide.md, hãy xây dựng bộ kiểm thử tích hợp hoàn chỉnh cho Backend:

1. Tạo tests/conftest.py:
   - Fixture thiết lập test database riêng biệt (PostgreSQL test schema).
   - Fixture AsyncClient của httpx kết nối với FastAPI app.
   - Fixture tạo sẵn tài khoản Admin, Học viên mẫu và Header chứa Bearer token tương ứng.
   - Mock các dịch vụ bên ngoài: Mock hàm gửi email mailer.send_otp_email, Mock OpenAI API calls (embedding & chat completion), Mock PayOS SDK.

2. Tạo tests/test_auth.py:
   - Test đăng ký tài khoản thành công -> Nhận mã OTP.
   - Test xác thực OTP đúng -> Nhận access_token và refresh_token.
   - Test xác thực OTP sai quá 5 lần -> Bị khóa theo BR-02.
   - Test đăng nhập sai mật khẩu -> Trả 401 UNAUTHORIZED.

3. Tạo tests/test_courses.py:
   - Test học viên chưa mua khóa học truy cập bài giảng có phí -> Bị chặn 403 NOT_ENROLLED.
   - Test học viên truy cập bài học thử (is_trial_allowed=True) -> Thành công HTTP 200.
   - Test Admin xuất bản khóa học khi chưa đủ điều kiện (video chưa xong) -> Bị từ chối 400 theo BR-06.
   - Test cập nhật tiến độ xem video mỗi 5s và khôi phục vị trí xem dở theo BR-12.

4. Tạo tests/test_ai_rag.py:
   - Test hỏi đáp AI: Gửi câu hỏi hợp lệ -> Trả về câu trả lời kèm danh sách trích dẫn sources có start_time, end_time.
   - Test hỏi ngoài phạm vi bài giảng -> Nhận HTTP 200 kèm is_out_of_scope=true, sources rỗng và câu trả lời từ chối theo mẫu (BR-10).
   - Test vượt hạn mức 50 câu hỏi/ngày -> Nhận lỗi 429 AI_QUOTA_EXCEEDED.
   - Test tóm tắt bài giảng: Kiểm tra cơ chế cache trả về is_cached=True cho lần gọi thứ hai (BR-11).

5. Tạo tests/test_payments.py:
   - Test tạo đơn hàng mua khóa học -> Nhận mã QR VietQR.
   - Test gọi Webhook PayOS lần đầu -> Đơn chuyển sang 'paid' và học viên tự động được ghi danh khóa học.
   - Test gọi Webhook PayOS lần thứ hai với cùng payload (Idempotency) -> Trả về HTTP 200 và không tạo ghi danh trùng lặp.

Hãy xuất mã nguồn chi tiết của toàn bộ file test, sử dụng pytest-asyncio chuẩn xác.
```
