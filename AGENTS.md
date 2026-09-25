# AGENTS.md — Quy Ước Bắt Buộc Cho AI Coding Agent (Backend)

> Đây là **file luật duy nhất** phải nạp trước khi viết bất kỳ dòng code nào.
> File này tóm tắt các quyết định **đã chốt** trong `docs/`. Khi có xung đột, tài liệu chi tiết trong `docs/` là nguồn chân lý.
> Không cần đọc lại toàn bộ `docs/` mỗi phiên: chỉ đọc file chuyên môn tương ứng (xem mục 2).

---

## 1. Bối cảnh & Ngăn xếp (đã chốt — không tự ý thay đổi)

Dự án: nền tảng học trực tuyến tích hợp AI Trợ giảng theo ngữ cảnh bài giảng.
Backend phục vụ 2 client: Mobile App Android (học viên) và Web Admin (quản trị viên).

| Thành phần | Công nghệ chốt |
|---|---|
| Ngôn ngữ / API | Python `>= 3.11`, FastAPI, Pydantic v2, Pydantic Settings |
| ORM / Migration | SQLAlchemy 2.0 (async) + Alembic |
| Cơ sở dữ liệu | **Supabase PostgreSQL + pgvector** |
| Lưu trữ đối tượng | **Cloudflare R2** |
| Xử lý media | FFmpeg + ffprobe (tự mã hóa HLS), Whisper (STT tiếng Việt) |
| Embedding | OpenAI `text-embedding-3-small` (1536 chiều, cosine) |
| LLM | GPT-4o-mini (chính), Gemini Flash (dự phòng) |
| Thanh toán | PayOS (VietQR, webhook HMAC, idempotent) — *dự kiến* |
| Kiểm thử / chất lượng | pytest + pytest-asyncio, httpx, ruff, mypy |

### 1.1 Cloud-only — quy tắc tuyệt đối
- **Toàn bộ môi trường (dev / test / prod) dùng chung** Supabase PostgreSQL + pgvector và Cloudflare R2.
- **Không** tạo Dockerfile/docker-compose để chạy PostgreSQL, **không** dùng container `pgvector/pgvector:pg16`, **không** dùng MinIO hay bất kỳ cơ sở dữ liệu/lưu trữ cục bộ nào.
- Mọi truy cập lưu trữ đi qua `Storage Adapter`; mọi truy cập mô hình AI đi qua `AI Adapter`.
- AWS S3 **chỉ** là hướng migration tương lai, không xuất hiện trong pipeline hiện tại.

### 1.2 Tài liệu không nằm trong repo này
`docs/01_Feature_Screen_Inventory.md` và `docs/03*`–`docs/07*` là tài liệu **Frontend**, không có trong repo Backend.
**Không** cố đọc các file này; khi cần dữ liệu trao đổi FE–BE thì dùng `docs/08_FE_BE_Data_Contract.md`.

---

## 2. Bản Đồ Tài Liệu — Đọc Gì Cho Việc Gì

| Việc cần làm | Đọc |
|---|---|
| Hiểu quy tắc nghiệp vụ, vòng đời, trạng thái | `docs/00_SYSTEM_BUSINESS_ANALYSIS.md` |
| Hiểu luồng người dùng | `docs/02_Use_Case_Specification.md` |
| Viết router / schema request-response / mã lỗi | `docs/08_FE_BE_Data_Contract.md` |
| Viết model, migration, chỉ mục pgvector, ma trận truy vết | `docs/09_BE_Database_Schema.md` |
| Viết tầng service, adapter, worker | `docs/10_BE_Architecture.md` |
| Viết pipeline video/AI (HLS, Whisper, chunk, RAG) | `docs/11_BE_AI_Pipeline_Spec.md` |
| Biết thứ tự triển khai, seed, triển khai & vận hành | `docs/12_BE_Implementation_Guide.md` |
| Chuỗi prompt viết code theo bước | `docs/BE_Coding_Prompt_Chain.md` |
| Quy ước bắt buộc (file này) | `AGENTS.md` |

---

## 3. Nguyên Tắc Kiến Trúc (luật phụ thuộc)

```text
Router -> Middleware/Permission -> Service -> Repository -> Database
                                        \-> Adapters (storage / ai / payos / mailer)
```

- Luồng hợp lệ: `router -> service -> repository -> db`.
- **Cấm:** router gọi trực tiếp repository hoặc adapter; repository gọi service; adapter gọi service.
- Adapter **chỉ** được gọi từ `service` hoặc `worker`, không gọi từ `router`.
- Một module nghiệp vụ **không** tự viết truy vấn vào bảng của module khác; điều phối qua service hoặc truy vấn đọc đặt trong module sở hữu dữ liệu.
- **Ranh giới giao dịch nằm ở tầng service.** Repository chỉ nhận session hiện hành và thao tác dữ liệu.
- Không giữ transaction cơ sở dữ liệu mở trong lúc chờ dịch vụ ngoài (email, AI, PayOS, R2). Ghi trạng thái trung gian trước, cập nhật kết quả sau bằng thao tác idempotent.
- Mọi thay đổi lược đồ **bắt buộc** đi qua Alembic; không sửa cơ sở dữ liệu thủ công.
- Các luồng bắt buộc nguyên tử: xác minh OTP; ghi danh miễn phí; webhook PayOS (`paid` + tạo `enrollments`); nộp bài + chấm điểm; sửa transcript + tăng phiên bản + tạo yêu cầu lập chỉ mục lại; retry pipeline step.

## 4. Quy Ước Mã Nguồn

- `snake_case` cho thư mục, file, hàm, biến; `PascalCase` cho class và Pydantic model.
- Mỗi module nghiệp vụ có **đúng 4 file**: `router.py`, `schemas.py`, `service.py`, `repository.py`.
- Tên trường request/response **phải khớp** `docs/08` (không tự đổi tên, không tự thêm/bớt).
- Hằng số dùng chung (mã lỗi, vai trò, trạng thái pipeline/đơn hàng) đặt trong `app/core/` hoặc enum trung tâm; không để mỗi module tự định nghĩa một biến thể.
- Truy vấn dùng SQLAlchemy 2.0 async; tránh n+1 (dùng `selectinload`/`joinedload` hoặc một truy vấn tổng hợp).
- Không log bí mật, mật khẩu gốc, OTP gốc, refresh token gốc, chữ ký webhook.
- Chú thích và thông điệp lỗi cho người dùng viết bằng tiếng Việt.

---

## 5. Hợp Đồng API Bắt Buộc

**Định dạng lỗi (mọi endpoint):**
```json
{ "error": { "code": "SCREAMING_SNAKE_CASE", "message": "Thông điệp tiếng Việt", "details": null } }
```

**Thành công — một đối tượng:** `{ "data": { ... }, "message": "OK" }`

**Thành công — danh sách phân trang:** `{ "data": [], "total": 0, "page": 1, "page_size": 20, "total_pages": 0 }`
Query params chuẩn: `page` (mặc định 1), `page_size` (mặc định 20).

**Nhóm mã lỗi:** `VALIDATION_ERROR` 400 · `UNAUTHORIZED`/`TOKEN_EXPIRED` 401 · `FORBIDDEN`/`NOT_ENROLLED` 403 · `NOT_FOUND` 404 · `EMAIL_ALREADY_EXISTS`/`CONFLICT_*`/`ALREADY_*` 409 · `AI_OUT_OF_SCOPE` 422 · `AI_QUOTA_EXCEEDED`/`RATE_LIMITED` 429 · `FILE_TOO_LARGE` 413 · `INVALID_FILE_FORMAT` 400 · `INTERNAL_ERROR`/`PAYMENT_GATEWAY_ERROR`/`AI_PROVIDER_ERROR` 500–502.

Tổng số endpoint theo hợp đồng `08`: **75**. Liệt kê đầy đủ ở PHỤ LỤC D của `docs/08`.

---

## 6. Hằng Số Vận Hành (nguồn: `docs/09` mục 5.5 và DE-09)

| Tham số | Giá trị |
|---|---|
| Access token TTL | 900 giây |
| Refresh token TTL | 7 ngày (mobile), 24 giờ (admin) |
| OTP | 6 chữ số, hiệu lực 300 giây, tối đa 5 lần sai trong 15 phút, dùng 1 lần |
| Đơn hàng hết hạn | 15 phút |
| Giới hạn tải lên | mỗi phần dưới 200MB, toàn bộ video tối đa 5GB |
| Bước pipeline | `upload`, `transcode`, `transcribe`, `index` |
| Chunk transcript | 500 token, chồng lấp 80–100 token |
| Embedding | `text-embedding-3-small`, 1536 chiều, cosine, phiên bản v1 |
| Truy xuất | Top-K = 5, ngưỡng tương đồng 0.72, cửa sổ tăng trọng 120 giây |
| Hạn mức AI | 50 câu hỏi/ngày/học viên, 10 lượt tóm tắt/ngày/học viên |
| Timeout AI | 30 giây mỗi lần gọi, tối đa 60 giây cho chuỗi chính + dự phòng |
| Fallback LLM | thử GPT-4o-mini 1 lần, lỗi 429/503/timeout thì Gemini Flash 1 lần |
| Polling | pipeline 10 giây (admin), trạng thái thanh toán 3 giây (mobile) |
| Sai số phụ đề | cộng trừ 0.5 giây (BR-15) |
| Ghi vị trí xem | mỗi 5–10 giây (BR-12) |

Giá trị lưu tại bảng `system_settings`; không hard-code rải rác trong code.

## 7. Tên Gọi & Trạng Thái (DE-02, DE-03)

- Tầng dữ liệu/API dùng: video `completed`, đơn hàng `paid`, bước pipeline `pending | processing | completed | failed`.
- Tên nghiệp vụ `Ready` / `Success` **chỉ** dùng cho mô tả và hiển thị.
- Hợp đồng `08` có thể ghi bước phiên âm là `stt`; tên chính thức là `transcribe` (ánh xạ khi cần tương thích).

---

## 8. Cấu Trúc Thư Mục

```text
app/
  main.py
  core/            # config.py, security.py, permissions.py, rate_limit.py, errors.py, constants.py
  db/              # session.py, models/, migrations/
  modules/<ten>/   # router.py, schemas.py, service.py, repository.py
  workers/         # video_pipeline.py, reindex.py, order_expiry.py
  adapters/        # storage.py, mailer.py, payos.py, ai/{whisper,embeddings,llm,prompts}
tests/             # conftest.py, test_*.py
requirements.txt
pyproject.toml     # cấu hình ruff / mypy / pytest
.env.example
```

---

## 9. Lệnh Chuẩn

```bash
python -m venv venv && venv/Scripts/activate      # Windows; Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head                               # áp dụng migration lên Supabase
uvicorn app.main:app --reload --port 8000          # chạy API
python -m app.workers.video_pipeline               # chạy worker (khi đã có)
python scripts/seed.py                             # nạp dữ liệu mẫu (không chạy trên prod)
pytest -q                                          # chạy test
ruff check . && ruff format .                      # lint + format
mypy app                                           # kiểm tra kiểu
```

- Kiểm thử tầng dữ liệu chỉ chạy khi có `TEST_DATABASE_URL`. **Nếu biến này để trống, test cần DB phải tự động SKIP**, không được báo lỗi.
- Khi chưa khai báo `TEST_DATABASE_URL`, chỉ chạy test dùng mock cho tầng service/logic.

---

## 10. Do / Don't

**DO**
- Đọc mục 2 để chọn đúng tài liệu trước khi code.
- Giữ tên trường khớp `docs/08`; giữ tên bảng/cột khớp `docs/09`.
- Bọc mọi dịch vụ ngoài sau adapter; inject qua Dependency Injection.
- Ghi trạng thái trung gian trước khi gọi dịch vụ ngoài; xử lý idempotent khi nhận kết quả.
- Trả lỗi đúng cấu trúc `{ "error": { code, message, details } }`.
- Xử lý file an toàn: dọn tệp tạm trong `finally`.

**DON'T**
- ❌ Dùng cơ sở dữ liệu hoặc lưu trữ cục bộ (MinIO, container pgvector, PostgreSQL local).
- ❌ `import boto3` hoặc SDK nhà cung cấp AI trong `service` / `worker` / `router`.
- ❌ Sửa cơ sở dữ liệu thủ công hoặc sửa migration đã áp dụng.
- ❌ Đổi tên trường API, đổi giá trị enum trạng thái, hoặc thêm endpoint ngoài `docs/08` mà không cập nhật tài liệu.
- ❌ Commit `.env`, khóa bí mật hoặc dữ liệu thật.
- ❌ Để `router` chứa quy tắc nghiệp vụ.
- ❌ Dùng `print()` để ghi log; dùng logging JSON có `request_id`.

---

## 11. Định Nghĩa Hoàn Thành (kiểm tra nhanh)

- [ ] `ruff check .` và `mypy app` không lỗi.
- [ ] `pytest -q` chạy được; test cần DB tự SKIP khi thiếu `TEST_DATABASE_URL`.
- [ ] Mọi response lỗi đúng cấu trúc chuẩn; response danh sách đúng wrapper phân trang.
- [ ] Tên trường khớp `docs/08`; tên bảng/cột khớp `docs/09`.
- [ ] Không có cấu hình cơ sở dữ liệu/lưu trữ cục bộ trong repo.
- [ ] Thay đổi lược đồ đi kèm migration Alembic.
