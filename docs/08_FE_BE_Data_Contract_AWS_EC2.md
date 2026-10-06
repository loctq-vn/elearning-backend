# FE–BE Data Contract

> **Dự án:** Xây dựng nền tảng học trực tuyến thông minh tích hợp AI Trợ giảng tương tác ngữ cảnh bài giảng  
> **Phiên bản:** 1.1 — Ngày tạo: 08/09/2026
> **Cập nhật hạ tầng:** 05/10/2026 — đồng bộ với kiến trúc AWS tại tài liệu `09`, `10`, `11`.  
> **Nguồn tham chiếu:** `07_FE_Logic_Interaction_Spec.md` (tài liệu Frontend, **không nằm trong repo Backend này**)  
> **Mục đích:** Định nghĩa chính xác dữ liệu trao đổi FE ↔ BE cho **mọi** màn hình/luồng, dùng làm cơ sở thiết kế API phía Backend (FastAPI).

---

## Quy ước tài liệu

| Ký hiệu | Ý nghĩa |
|----------|----------|
| ✅ | Field bắt buộc |
| ❌ | Field không bắt buộc |
| `→` | Chiều dữ liệu (FE gửi lên / BE trả về) |
| `[M-XX]` | Màn hình Mobile App |
| `[A-XX]` | Màn hình Web Admin |
| `PK` | Primary Key |
| `FK` | Foreign Key |
| `enum(...)` | Giá trị hạn chế trong tập cho trước |

**Base URL:** `https://api.example.com`  
**Content-Type mặc định:** `application/json`  
**Authentication:** `Authorization: Bearer <access_token>` (trừ các endpoint public)  
**Pagination chung:** Query params `page` (int, default 1) + `page_size` (int, default 20). Response wrapper: `{ data: [...], total: int, page: int, page_size: int, total_pages: int }`

**Quy ước response lỗi chung (áp dụng cho mọi endpoint):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `error.code` | `string` | Mã lỗi dạng `SCREAMING_SNAKE_CASE` |
| `error.message` | `string` | Thông điệp cho người dùng (tiếng Việt, đã có trong danh mục mã lỗi) |
| `error.details` | `object?` | Chi tiết lỗi từng trường (chỉ có ở 400 VALIDATION_ERROR / 422) |

Bảng mã lỗi chuẩn toàn hệ thống (các mục sau chỉ tham chiếu, không định nghĩa lại):

| Error Code | HTTP | Nhóm |
|-----------|------|------|
| `VALIDATION_ERROR` | 400 | Kiểm tra dữ liệu đầu vào |
| `UNAUTHORIZED` / `TOKEN_EXPIRED` | 401 | Xác thực |
| `FORBIDDEN` / `NOT_ENROLLED` | 403 | Phân quyền |
| `NOT_FOUND` | 404 | Tài nguyên |
| `EMAIL_ALREADY_EXISTS`, `CONFLICT_*`, `ALREADY_*` | 409 | Xung đột trạng thái |
| `AI_QUOTA_EXCEEDED` | 429 | Hết hạn mức hỏi đáp/tóm tắt trong ngày |
| `AI_OUT_OF_SCOPE` | 422 | **(ngừng dùng)** — trường hợp hỏi ngoài phạm vi nay trả HTTP 200 kèm `is_out_of_scope = true`; giữ dòng này để tương thích tài liệu cũ |
| `SUMMARY_TOO_SHORT` / `TRANSCRIPT_TOO_SHORT` | 400 | Nội dung quá ngắn để tóm tắt |
| `FILE_TOO_LARGE`, `INVALID_FILE_FORMAT` | 413 / 400 | Tải lên |
| `RATE_LIMITED` | 429 | Giới hạn tần suất |
| `INTERNAL_ERROR`, `PAYMENT_GATEWAY_ERROR`, `AI_PROVIDER_ERROR` | 500 / 502 | Hệ thống và tích hợp |

---

## 1. AUTHENTICATION (Xác thực)

> Màn hình: `M-03`, `M-04`, `M-05`, `A-01`

---

### 1.1 Đăng ký tài khoản học viên

| # | Hành động | Endpoint |
|---|-----------|----------|
| 1.1 | Học viên đăng ký tài khoản mới | `POST /api/auth/register` |

**FE gửi lên (Request Body):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `full_name` | `string` | ✅ | Họ tên, 2–100 ký tự, chỉ chữ cái + khoảng trắng + dấu tiếng Việt |
| `email` | `string` | ✅ | Email hợp lệ, max 255 ký tự |
| `password` | `string` | ✅ | ≥ 8 ký tự, chứa chữ hoa + thường + số + ký tự đặc biệt |

**BE trả về (Response 201):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Đăng ký thành công. Mã OTP đã gửi đến email."` |
| `email` | `string` | Email đã đăng ký (dùng hiển thị ở bước OTP) |
| `otp_expires_in` | `int` | Thời gian hiệu lực OTP tính bằng giây (VD: `300`) |

**Mã lỗi cần phân biệt:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `VALIDATION_ERROR` | Thiếu/sai dữ liệu đầu vào | Inline error per field |
| `409` | `EMAIL_ALREADY_EXISTS` | Email đã được đăng ký | Inline: "Email này đã được đăng ký. [Đăng nhập ngay]" |
| `429` | `RATE_LIMITED` | Gửi quá nhiều request | Modal countdown |
| `500` | `INTERNAL_ERROR` | Lỗi hệ thống | Snackbar "Đã xảy ra lỗi hệ thống" |

---

### 1.2 Xác thực OTP (Đăng ký / Quên mật khẩu)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 1.2 | Học viên gửi mã OTP xác thực | `POST /api/auth/verify-otp` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `email` | `string` | ✅ | Email đã đăng ký |
| `otp_code` | `string` | ✅ | Mã 6 chữ số |
| `purpose` | `string` | ✅ | `enum("registration", "password_reset")` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `access_token` | `string` | JWT access token (nếu `purpose = registration` → auto-login) |
| `refresh_token` | `string` | Refresh token (nếu `purpose = registration`) |
| `token_type` | `string` | `"Bearer"` |
| `expires_in` | `int` | Access token TTL (giây), VD: `900` (15 phút) |
| `reset_token` | `string` | Token dùng cho bước đặt lại mật khẩu (nếu `purpose = password_reset`) |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `INVALID_OTP` | Mã OTP không đúng | Inline: "Mã xác nhận không đúng". Clear ô OTP. |
| `400` | `OTP_EXPIRED` | Mã OTP đã hết hạn | Text: "Mã đã hết hạn". Enable nút "Gửi lại mã". |
| `429` | `OTP_ATTEMPTS_EXCEEDED` | Nhập sai quá 5 lần | Modal: "Bạn đã nhập sai quá nhiều lần. Thử lại sau 15 phút." |
| `404` | `EMAIL_NOT_FOUND` | Email không tồn tại | (Không phân biệt — trả 400 chung để bảo mật) |

---

### 1.3 Gửi lại OTP

| # | Hành động | Endpoint |
|---|-----------|----------|
| 1.3 | Gửi lại mã OTP | `POST /api/auth/resend-otp` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `email` | `string` | ✅ | Email cần gửi lại OTP |
| `purpose` | `string` | ✅ | `enum("registration", "password_reset")` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Mã OTP mới đã được gửi."` |
| `otp_expires_in` | `int` | TTL mới (giây) |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `429` | `RESEND_COOLDOWN` | Gửi lại quá nhanh | Toast: "Vui lòng chờ trước khi gửi lại mã." |
| `500` | `EMAIL_SEND_FAILED` | Lỗi gửi email | Toast: "Không thể gửi lại mã. Vui lòng thử lại." |

---

### 1.4 Đăng nhập

| # | Hành động | Endpoint |
|---|-----------|----------|
| 1.4 | Học viên / Admin đăng nhập | `POST /api/auth/login` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `email` | `string` | ✅ | Email đã đăng ký |
| `password` | `string` | ✅ | Mật khẩu |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `access_token` | `string` | JWT access token |
| `refresh_token` | `string` | Refresh token |
| `token_type` | `string` | `"Bearer"` |
| `expires_in` | `int` | Access token TTL (giây) |
| `user` | `object` | Thông tin user cơ bản (xem bảng dưới) |

**Object `user`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK user |
| `full_name` | `string` | Họ tên |
| `email` | `string` | Email |
| `avatar_url` | `string?` | URL ảnh đại diện (nullable) |
| `role` | `string` | `enum("student", "admin")` |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `401` | `INVALID_CREDENTIALS` | Email hoặc mật khẩu sai | Inline chung: "Email hoặc mật khẩu không đúng" + shake animation |
| `403` | `EMAIL_NOT_VERIFIED` | Tài khoản chưa xác thực email | Snackbar: "Tài khoản chưa được xác thực" + action "Gửi lại mã" |
| `403` | `ACCOUNT_LOCKED` | Tài khoản bị khóa vĩnh viễn | Modal: "Tài khoản đã bị khóa. Liên hệ quản trị viên." |
| `429` | `LOGIN_RATE_LIMITED` | Đăng nhập sai quá nhiều lần | Modal countdown: "Thử lại sau [MM:SS]" |

---

### 1.5 Refresh Token

| # | Hành động | Endpoint |
|---|-----------|----------|
| 1.5 | Làm mới access token | `POST /api/auth/refresh` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `refresh_token` | `string` | ✅ | Refresh token hiện tại |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `access_token` | `string` | JWT mới |
| `refresh_token` | `string` | Refresh token mới (rotation) |
| `expires_in` | `int` | TTL access token (giây) |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `401` | `REFRESH_TOKEN_INVALID` | Token không hợp lệ hoặc đã bị thu hồi | Xóa token local → redirect login + toast "Phiên đăng nhập đã hết hạn" |
| `401` | `REFRESH_TOKEN_EXPIRED` | Token hết hạn | Tương tự trên |

---

### 1.6 Đăng xuất

| # | Hành động | Endpoint |
|---|-----------|----------|
| 1.6 | Đăng xuất (học viên / admin) | `POST /api/auth/logout` |

**FE gửi lên (Header):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `Authorization` | `string` | ✅ | `Bearer <access_token>` |

**FE gửi lên (Body):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `refresh_token` | `string` | ❌ | Refresh token cần invalidate (nếu client có) |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Đăng xuất thành công"` |

> ⚠️ FE gọi best-effort — nếu API fail (mất mạng) thì vẫn xóa token local + redirect.

---

### 1.7 Quên mật khẩu — Gửi email

| # | Hành động | Endpoint |
|---|-----------|----------|
| 1.7 | Yêu cầu đặt lại mật khẩu | `POST /api/auth/forgot-password` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `email` | `string` | ✅ | Email cần đặt lại mật khẩu |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Nếu email tồn tại, mã xác nhận sẽ được gửi."` |
| `otp_expires_in` | `int` | TTL OTP (giây) |

> ⚠️ Luôn trả 200 dù email có tồn tại hay không (bảo mật — tránh lộ thông tin).

---

### 1.8 Đặt lại mật khẩu

| # | Hành động | Endpoint |
|---|-----------|----------|
| 1.8 | Đặt mật khẩu mới | `POST /api/auth/reset-password` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `reset_token` | `string` | ✅ | Token nhận từ bước verify OTP (purpose = password_reset) |
| `new_password` | `string` | ✅ | Mật khẩu mới (cùng quy tắc đăng ký) |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Mật khẩu đã được đặt lại thành công."` |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `INVALID_RESET_TOKEN` | Token reset không hợp lệ / hết hạn | Modal: "Liên kết đặt lại đã hết hạn. Vui lòng thử lại." |
| `400` | `PASSWORD_TOO_WEAK` | Mật khẩu không đủ mạnh | Inline error |

---

## 2. KHÓA HỌC & BÀI GIẢNG

> Màn hình: `M-06`, `M-07`, `M-08`, `M-09`, `M-12`, `M-21`, `A-03`, `A-04`, `A-05`, `A-06`, `A-14`, `A-15`

---

### 2.1 Lấy danh sách khóa học nổi bật (Home banner)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.1 | Trang chủ — banner carousel | `GET /api/courses/featured` |

**FE gửi lên (Query Params):** Không có.

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `array[FeaturedCourse]` | Danh sách khóa học nổi bật (5–10 items) |

**Object `FeaturedCourse`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK khóa học |
| `title` | `string` | Tên khóa học |
| `thumbnail_url` | `string` | URL ảnh bìa (ratio 16:9) |
| `price` | `int` | Giá (VND), `0` = miễn phí |
| `original_price` | `int?` | Dự phòng giai đoạn 2 — giá gốc (nullable, hiện trả `null` / FE không phụ thuộc) |
| `rating_avg` | `float?` | Dự phòng giai đoạn 2 — đánh giá trung bình (0.0–5.0), hiện có thể trả `null` |
| `enrolled_count` | `int` | Tổng số học viên đã đăng ký |
| `banner_url` | `string?` | Dự phòng giai đoạn 2 — URL ảnh banner riêng (nullable, hiện trả `null` / FE không phụ thuộc) |
| `instructor_name` | `string` | Tên giảng viên phụ trách |
| `instructor_avatar_url` | `string?` | URL avatar giảng viên (nullable) |

---

### 2.2 Lấy danh sách "Tiếp tục học"

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.2 | Trang chủ — section "Tiếp tục học" | `GET /api/progress/continue` |

**FE gửi lên:** Header `Authorization` (bắt buộc).

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `array[ContinueLearning]` | Danh sách khóa đang học, sort theo `last_watched_at` desc |

**Object `ContinueLearning`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `course_id` | `string (UUID)` | FK khóa học |
| `course_title` | `string` | Tên khóa học |
| `course_thumbnail_url` | `string` | Ảnh bìa |
| `next_lesson_id` | `string (UUID)` | Bài giảng tiếp theo chưa hoàn thành |
| `next_lesson_title` | `string` | Tên bài giảng tiếp |
| `last_position` | `float` | Vị trí dừng cuối (giây) |
| `progress_percent` | `float` | % hoàn thành khóa học (0.0–100.0) |
| `last_watched_at` | `string (ISO 8601)` | Thời điểm xem gần nhất |

---

### 2.3 Lấy danh sách khóa học (Khám phá / Tìm kiếm)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.3 | Duyệt / tìm / lọc khóa học | `GET /api/courses` |

**FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `page` | `int` | ❌ | Trang hiện tại (default: `1`) |
| `page_size` | `int` | ❌ | Số item/trang (default: `20`) |
| `search` | `string` | ❌ | Từ khóa tìm kiếm (tên khóa học) |
| `category_id` | `string (UUID)` | ❌ | Lọc theo danh mục |
| `instructor_id` | `string (UUID)` | ❌ | Lọc theo giảng viên phụ trách |
| `price_min` | `int` | ❌ | Giá tối thiểu (VND) |
| `price_max` | `int` | ❌ | Giá tối đa (VND) |
| `sort_by` | `string` | ❌ | `enum("newest", "recommended", "price_asc", "price_desc")`. Default: `"newest"` |
| `status` | `string` | ❌ | (Admin only) `enum("published", "draft", "hidden")` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `array[CourseListItem]` | Danh sách khóa học |
| `total` | `int` | Tổng số kết quả |
| `page` | `int` | Trang hiện tại |
| `page_size` | `int` | Số item/trang |
| `total_pages` | `int` | Tổng số trang |

**Object `CourseListItem`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `title` | `string` | Tên khóa học |
| `thumbnail_url` | `string` | Ảnh bìa |
| `price` | `int` | Giá (VND) |
| `original_price` | `int?` | Dự phòng giai đoạn 2 — giá gốc (nullable, hiện trả `null` / FE không phụ thuộc) |
| `rating_avg` | `float?` | Dự phòng giai đoạn 2 — đánh giá TB, hiện có thể trả `null` |
| `rating_count` | `int?` | Dự phòng giai đoạn 2 — số lượt đánh giá, hiện có thể trả `null` |
| `enrolled_count` | `int` | Số học viên |
| `category_name` | `string` | Tên danh mục |
| `instructor_name` | `string` | Tên giảng viên phụ trách |
| `instructor_avatar_url` | `string?` | URL avatar giảng viên (nullable) |
| `status` | `string` | (Admin view only) `enum("published", "draft", "hidden")` |
| `created_at` | `string (ISO 8601)` | Ngày tạo |

---

### 2.4 Lấy danh sách danh mục

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.4 | Lấy danh mục cho chip filter / dropdown | `GET /api/categories` |

**FE gửi lên:** Không có query params.

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `array[Category]` | Danh sách danh mục |

**Object `Category`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `name` | `string` | Tên danh mục |
| `course_count` | `int` | Số khóa học trong danh mục |

---

### 2.5 Lấy chi tiết khóa học

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.5 | Xem chi tiết 1 khóa học | `GET /api/courses/{course_id}` |

**FE gửi lên:** Path param `course_id`. Header `Authorization` (optional — nếu có thì trả thêm enrollment info).

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `title` | `string` | Tên khóa học |
| `description` | `string` | Mô tả (HTML rich text) |
| `thumbnail_url` | `string` | Ảnh bìa |
| `price` | `int` | Giá (VND) |
| `original_price` | `int?` | Dự phòng giai đoạn 2 — giá gốc (nullable, hiện trả `null` / FE không phụ thuộc) |
| `rating_avg` | `float?` | Dự phòng giai đoạn 2 — đánh giá TB, hiện có thể trả `null` |
| `rating_count` | `int?` | Dự phòng giai đoạn 2 — số lượt đánh giá, hiện có thể trả `null` |
| `enrolled_count` | `int` | Số học viên |
| `category` | `Category` | Object danh mục |
| `instructor` | `InstructorProfile` | Hồ sơ giảng viên phụ trách (xem bảng dưới) |
| `is_enrolled` | `boolean` | `true` nếu user đã mua / đăng ký |
| `progress_percent` | `float?` | % hoàn thành (nullable nếu chưa enrolled) |
| `chapters` | `array[Chapter]` | Cấu trúc nội dung (xem bảng dưới) |
| `total_lessons` | `int` | Tổng số bài giảng |
| `total_duration` | `int` | Tổng thời lượng (giây) |
| `created_at` | `string (ISO 8601)` | Ngày tạo |
| `updated_at` | `string (ISO 8601)` | Ngày cập nhật |

**Object `InstructorProfile`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK giảng viên |
| `name` | `string` | Họ tên giảng viên |
| `title` | `string` | Học vị / Chuyên môn (VD: Thạc sĩ Khoa học Máy tính) |
| `bio` | `string?` | Tiểu sử giảng viên |
| `avatar_url` | `string?` | URL ảnh đại diện |

**Object `Chapter`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK chương |
| `title` | `string` | Tên chương |
| `order` | `int` | Thứ tự |
| `lessons` | `array[LessonSummary]` | Danh sách bài trong chương |

**Object `LessonSummary`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK bài giảng |
| `title` | `string` | Tên bài |
| `order` | `int` | Thứ tự |
| `duration` | `int` | Thời lượng (giây) |
| `is_locked` | `boolean` | `true` nếu chưa mua & bài có phí |
| `is_completed` | `boolean?` | `true/false` nếu đã enrolled, `null` nếu chưa |
| `has_quiz` | `boolean` | Có quiz giữa video hay không |
| `has_exercise` | `boolean` | Có bài tập cuối bài hay không |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `404` | `COURSE_NOT_FOUND` | Khóa học không tồn tại hoặc đã bị gỡ | Card lỗi: "Khóa học không tồn tại" + nút "Quay lại" |

---

### 2.6 Đăng ký khóa học miễn phí

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.6 | Học viên đăng ký khóa miễn phí | `POST /api/courses/{course_id}/enroll` |

**FE gửi lên:** Path param `course_id`. Header `Authorization` bắt buộc.

**BE trả về (Response 201):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `enrollment_id` | `string (UUID)` | PK enrollment |
| `course_id` | `string (UUID)` | FK khóa học |
| `first_lesson_id` | `string (UUID)` | Bài giảng đầu tiên để navigate |
| `enrolled_at` | `string (ISO 8601)` | Thời điểm đăng ký |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `COURSE_NOT_FREE` | Khóa học có phí, không thể enroll trực tiếp | Toast: "Vui lòng mua khóa học" |
| `409` | `ALREADY_ENROLLED` | Đã đăng ký rồi | Navigate trực tiếp đến bài giảng tiếp |

---

### 2.7 Lấy chi tiết bài giảng (Player data)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.7 | Tải dữ liệu trình phát video | `GET /api/lessons/{lesson_id}` |

**FE gửi lên:** Path param `lesson_id`. Header `Authorization` bắt buộc.

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK bài giảng |
| `title` | `string` | Tên bài |
| `description` | `string?` | Mô tả bài (nullable) |
| `course_id` | `string (UUID)` | FK khóa học |
| `chapter_id` | `string (UUID)` | FK chương |
| `hls_stream_url` | `string` | Signed HLS URL (TTL ~2h) |
| `duration` | `int` | Tổng thời lượng (giây) |
| `last_position` | `float` | Vị trí dừng cuối (giây), `0` nếu chưa xem |
| `transcript` | `array[TranscriptSegment]` | Danh sách phụ đề/transcript |
| `chapters` | `array[VideoChapter]` | Mốc chương trong video |
| `quiz_markers` | `array[QuizMarker]` | Mốc quiz giữa video |
| `next_lesson_id` | `string? (UUID)` | Bài giảng tiếp theo (nullable nếu bài cuối) |
| `prev_lesson_id` | `string? (UUID)` | Bài giảng trước (nullable nếu bài đầu) |

**Object `TranscriptSegment`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `start` | `float` | Thời điểm bắt đầu (giây, VD: `12.5`) |
| `end` | `float` | Thời điểm kết thúc |
| `text` | `string` | Nội dung phụ đề |

**Object `VideoChapter`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `title` | `string` | Tên chương/mốc |
| `start_time` | `float` | Thời điểm bắt đầu (giây) |

**Object `QuizMarker`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `quiz_id` | `string (UUID)` | PK quiz |
| `timestamp` | `float` | Mốc thời gian trigger (giây) |
| `is_answered` | `boolean` | Đã trả lời chưa |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `403` | `NOT_ENROLLED` | Chưa mua/đăng ký khóa học | Toast: "Vui lòng mua khóa học để truy cập" |
| `404` | `LESSON_NOT_FOUND` | Bài giảng không tồn tại | Card lỗi: "Video không tồn tại" |
| `503` | `VIDEO_NOT_READY` | Video chưa xử lý xong pipeline | Card lỗi: "Video chưa sẵn sàng" |

---

### 2.8 Lấy danh sách "Khóa học của tôi" (Thư viện)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.8 | Xem danh sách khóa đã mua/đăng ký | `GET /api/my-courses` |

**FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `status` | `string` | ❌ | `enum("in_progress", "completed")`. Default: tất cả |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `array[MyCourse]` | Danh sách khóa học của tôi |

**Object `MyCourse`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `course_id` | `string (UUID)` | FK khóa học |
| `title` | `string` | Tên khóa |
| `thumbnail_url` | `string` | Ảnh bìa |
| `progress_percent` | `float` | % hoàn thành |
| `next_lesson_id` | `string? (UUID)` | Bài tiếp (nullable nếu hoàn thành) |
| `next_lesson_title` | `string?` | Tên bài tiếp |
| `last_position` | `float` | Vị trí dừng cuối (giây) |
| `enrolled_at` | `string (ISO 8601)` | Ngày đăng ký |
| `completed_at` | `string? (ISO 8601)` | Ngày hoàn thành (nullable) |

---

### 2.9 Tạo khóa học (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.9 | Admin tạo khóa học mới | `POST /api/admin/courses` |

**FE gửi lên (`multipart/form-data`):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `title` | `string` | ✅ | 5–200 ký tự |
| `description` | `string` | ❌ | Rich text HTML, max 10.000 ký tự |
| `category_id` | `string (UUID)` | ✅ | FK danh mục |
| `instructor_id` | `string (UUID)` | ❌ | FK giảng viên phụ trách (bắt buộc khi xuất bản theo BR-17) |
| `price` | `int` | ✅ | Giá (VND), ≥ 0 |
| `status` | `string` | ✅ | `enum("draft", "published", "hidden")` |
| `thumbnail` | `file` | ❌ | JPEG/PNG/WebP, max 5MB |

> Khi tạo hoặc cập nhật khóa học với `status = "published"`, Backend bắt buộc kiểm tra điều kiện xuất bản theo BR-06 và BR-17: khóa học có tối thiểu 01 chương, các bài giảng bắt buộc đã có video ở trạng thái `completed`, và đã gán giảng viên phụ trách (`instructor_id` hợp lệ).

**BE trả về (Response 201):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK khóa học mới |
| `title` | `string` | Tên |
| `status` | `string` | Trạng thái |
| `created_at` | `string (ISO 8601)` | Thời điểm tạo |

---

### 2.10 Cập nhật khóa học (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.10 | Admin sửa khóa học | `PUT /api/admin/courses/{course_id}` |

**FE gửi lên (`multipart/form-data`):** Giống 2.9 (tất cả field optional — chỉ gửi field cần sửa).

**BE trả về (Response 200):** Object khóa học đầy đủ sau khi cập nhật.

**Mã lỗi khi xuất bản:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `409` | `COURSE_NOT_READY_TO_PUBLISH` | Khóa học chưa đủ điều kiện xuất bản theo BR-06 | Modal nêu các mục còn thiếu: chương, bài giảng, video chưa sẵn sàng |

---

### 2.11 Xóa khóa học (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.11 | Admin xóa khóa học | `DELETE /api/admin/courses/{course_id}` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Đã xóa khóa học thành công."` |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `409` | `COURSE_HAS_ENROLLMENTS` | Khóa học có học viên đang học | Modal cảnh báo → gợi ý ẩn thay vì xóa |

---

### 2.12 Quản lý cấu trúc bài giảng (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.12a | Thêm chương | `POST /api/admin/courses/{course_id}/chapters` |
| 2.12b | Sửa chương | `PUT /api/admin/chapters/{chapter_id}` |
| 2.12c | Xóa chương | `DELETE /api/admin/chapters/{chapter_id}` |
| 2.12d | Sắp xếp lại chương/bài | `PUT /api/admin/courses/{course_id}/reorder` |

**2.12a — Thêm chương — FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `title` | `string` | ✅ | Tên chương, 2–200 ký tự |
| `order` | `int` | ❌ | Vị trí (default: cuối) |

**2.12d — Sắp xếp lại — FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `chapters` | `array[{id: UUID, order: int, lessons: [{id: UUID, order: int}]}]` | ✅ | Thứ tự mới toàn bộ cấu trúc |

---

### 2.13 Tạo / Sửa bài giảng (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.13a | Tạo bài giảng | `POST /api/admin/chapters/{chapter_id}/lessons` |
| 2.13b | Sửa bài giảng | `PUT /api/admin/lessons/{lesson_id}` |
| 2.13c | Xóa bài giảng | `DELETE /api/admin/lessons/{lesson_id}` |

**2.13a — Tạo bài giảng — FE gửi lên (`multipart/form-data`):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `title` | `string` | ✅ | 5–200 ký tự |
| `description` | `string` | ❌ | Max 5.000 ký tự |
| `video` | `file` | ❌ | MP4/MOV/AVI/MKV/WEBM, max 5GB |
| `order` | `int` | ❌ | Vị trí trong chương |

**BE trả về (Response 201):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK bài giảng |
| `title` | `string` | Tên bài |
| `video_id` | `string? (UUID)` | ID video (nếu đã upload) |
| `pipeline_status` | `string?` | Giá trị rút gọn của `overall_status` (xem mục 9.2). Trạng thái chi tiết từng bước lấy qua `GET /api/admin/pipeline/{video_id}/status` |

> ⚠️ Quy ước thống nhất: trạng thái pipeline chỉ định nghĩa tại mục 9.2 (`overall_status` 5 giá trị) và object `PipelineStep` (4 bước). Mọi màn hình khác chỉ được **tham chiếu** các giá trị này, không phát minh giá trị mới.

---

### 2.14 Quản lý hồ sơ giảng viên (Admin CRUD)

> Màn hình: `A-14`, `A-15`, `A-04`  
> Nghiệp vụ: Giảng viên là Profile Master Data do Admin quản lý; không có role hay portal riêng (BR-17).

| # | Hành động | Endpoint |
|---|-----------|----------|
| 2.14a | Lấy danh sách giảng viên (Admin) | `GET /api/admin/instructors` |
| 2.14b | Lấy chi tiết hồ sơ giảng viên (Admin) | `GET /api/admin/instructors/{instructor_id}` |
| 2.14c | Tạo hồ sơ giảng viên mới (Admin) | `POST /api/admin/instructors` |
| 2.14d | Cập nhật hồ sơ giảng viên (Admin) | `PUT /api/admin/instructors/{instructor_id}` |
| 2.14e | Xóa / Ngưng cộng tác giảng viên (Admin) | `DELETE /api/admin/instructors/{instructor_id}` |
| 2.14f | Lấy danh sách giảng viên cho dropdown | `GET /api/instructors/options` |

**2.14a — Lấy danh sách giảng viên (Admin) — FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `page` | `int` | ❌ | Trang hiện tại (default: `1`) |
| `page_size` | `int` | ❌ | Số item/trang (default: `20`) |
| `search` | `string` | ❌ | Tìm theo họ tên, email |
| `status` | `string` | ❌ | `enum("all", "active", "suspended")`. Default: `"all"` |

**2.14a — BE trả về (Response 200):** Paginated list of `AdminInstructorItem` objects.

**Object `AdminInstructorItem`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK giảng viên |
| `name` | `string` | Họ và tên |
| `title` | `string` | Học vị / Chuyên môn |
| `email` | `string?` | Email liên hệ |
| `phone` | `string?` | Số điện thoại |
| `avatar_url` | `string?` | URL ảnh đại diện |
| `courses_count` | `int` | Số khóa học đang phụ trách |
| `is_active` | `boolean` | Trạng thái cộng tác |
| `created_at` | `string (ISO 8601)` | Ngày tạo |

**2.14b — Lấy chi tiết giảng viên — BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK giảng viên |
| `name` | `string` | Họ và tên |
| `title` | `string` | Học vị / Chuyên môn |
| `bio` | `string?` | Tiểu sử chi tiết |
| `avatar_url` | `string?` | URL ảnh đại diện |
| `email` | `string?` | Email liên hệ |
| `phone` | `string?` | Số điện thoại |
| `is_active` | `boolean` | Trạng thái cộng tác |
| `courses` | `array[InstructorAssignedCourse]` | Danh sách các khóa học phụ trách |
| `created_at` | `string (ISO 8601)` | Ngày tạo |
| `updated_at` | `string (ISO 8601)` | Ngày cập nhật |

**Object `InstructorAssignedCourse`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK khóa học |
| `title` | `string` | Tên khóa học |
| `thumbnail_url` | `string` | Ảnh bìa |
| `status` | `string` | `enum("draft", "published", "hidden")` |
| `enrolled_count` | `int` | Số học viên |

**2.14c — Tạo hồ sơ giảng viên — FE gửi lên (`multipart/form-data`):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `name` | `string` | ✅ | Họ tên (2–100 ký tự) |
| `title` | `string` | ✅ | Học vị / Chuyên môn (2–150 ký tự) |
| `bio` | `string` | ❌ | Tiểu sử (max 2.000 ký tự) |
| `email` | `string` | ❌ | Email liên hệ hợp lệ |
| `phone` | `string` | ❌ | Số điện thoại VN |
| `is_active` | `boolean` | ❌ | Default: `true` |
| `avatar` | `file` | ❌ | JPEG/PNG/WebP, max 3MB |

**2.14c — BE trả về (Response 201):** Object `AdminInstructorItem` của giảng viên vừa tạo.

**2.14d — Cập nhật hồ sơ giảng viên — FE gửi lên (`multipart/form-data`):** Giống 2.14c (tất cả các trường optional, chỉ gửi dữ liệu cần sửa).

**2.14d — BE trả về (Response 200):** Object chi tiết giảng viên sau cập nhật.

**2.14e — Xóa / Ngưng cộng tác — BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | Thông báo kết quả |
| `instructor_id` | `string (UUID)` | ID giảng viên vừa xử lý |
| `deleted` | `boolean` | `true` nếu xóa mềm thành công, `false` nếu chỉ chuyển `is_active = false` |

**Mã lỗi 2.14e:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `INSTRUCTOR_HAS_ACTIVE_COURSES` | Giảng viên đang phụ trách khóa học đã xuất bản | Toast/Dialog: "Không thể xóa giảng viên đang phụ trách khóa học đang phát hành. Vui lòng chuyển giao khóa học trước." |

**2.14f — Dropdown options giảng viên (Public / Admin):**

**BE trả về (Response 200):** `array[InstructorOption]`

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK giảng viên |
| `name` | `string` | Họ tên |
| `title` | `string` | Học vị / Chuyên môn |
| `avatar_url` | `string?` | Ảnh đại diện |

---

## 3. TIẾN ĐỘ HỌC TẬP

> Màn hình: `M-12`, `M-20`

---

### 3.1 Lưu tiến độ xem video

| # | Hành động | Endpoint |
|---|-----------|----------|
| 3.1 | Auto-save progress mỗi 10 giây | `POST /api/progress` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `lesson_id` | `string (UUID)` | ✅ | FK bài giảng |
| `current_position` | `float` | ✅ | Vị trí hiện tại (giây) |
| `total_duration` | `float` | ✅ | Tổng thời lượng (giây) |
| `completed` | `boolean` | ❌ | `true` khi `current_position >= total_duration * 0.9`. Default: `false` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"OK"` |
| `course_progress_percent` | `float` | % hoàn thành khóa học sau cập nhật |

> ⚠️ Endpoint này gọi rất thường xuyên (mỗi 10s). BE cần tối ưu performance (upsert, không tạo record mới mỗi lần).

---

### 3.2 Lấy tổng quan tiến độ học tập

| # | Hành động | Endpoint |
|---|-----------|----------|
| 3.2 | Xem trang tiến độ học tập | `GET /api/progress/overview` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `total_enrolled_courses` | `int` | Tổng khóa đã đăng ký |
| `total_hours_watched` | `float` | Tổng giờ đã học |
| `total_lessons_completed` | `int` | Tổng bài đã hoàn thành |
| `courses` | `array[CourseProgress]` | Chi tiết tiến độ từng khóa |

**Object `CourseProgress`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `course_id` | `string (UUID)` | FK khóa học |
| `course_title` | `string` | Tên khóa |
| `thumbnail_url` | `string` | Ảnh bìa |
| `progress_percent` | `float` | % hoàn thành |
| `completed_lessons` | `int` | Số bài đã hoàn thành |
| `total_lessons` | `int` | Tổng số bài |

---

## 4. AI Q&A — CHAT TRỢ GIẢNG (RAG)

> Màn hình: `M-13`

---

### 4.1 Gửi câu hỏi cho AI Trợ giảng

| # | Hành động | Endpoint |
|---|-----------|----------|
| 4.1 | Học viên gửi câu hỏi theo ngữ cảnh bài giảng | `POST /api/lessons/{lesson_id}/ask` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `question` | `string` | ✅ | Câu hỏi, 5–500 ký tự |
| `video_position_seconds` | `float` | ✅ | Vị trí video hiện tại (giây) — Backend dùng để khoanh vùng ngữ cảnh RAG. Đổi tên từ `current_timestamp` để tránh trùng với hàm SQL chuẩn. |
| `chat_history_ids` | `array[string]?` | ❌ | Danh sách ID tin nhắn trước (nếu cần context multi-turn) |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK tin nhắn AI |
| `answer` | `string` | Nội dung câu trả lời (Markdown format) |
| `sources` | `array[AISource]` | Danh sách nguồn trích dẫn từ transcript |
| `processing_time` | `float` | Thời gian xử lý (giây) |
| `questions_remaining` | `int` | Số lượt hỏi còn lại trong ngày |
| `daily_limit` | `int` | Giới hạn hỏi/ngày |
| `is_out_of_scope` | `boolean` | `true` khi câu hỏi không có căn cứ trong bài giảng (BR-10); khi đó `answer` là câu từ chối chuẩn và `sources` là mảng rỗng |

> Khi không có đoạn transcript nào đạt ngưỡng tương đồng 0.72, Backend **không** gọi mô hình ngôn ngữ mà trả ngay HTTP **200** kèm `is_out_of_scope = true`. Đây là kết quả nghiệp vụ bình thường, không phải lỗi. Mã lỗi `AI_OUT_OF_SCOPE` không còn được trả về cho trường hợp này.
>
> Câu hỏi bị từ chối **vẫn được ghi** vào `ai_qa_logs` và **vẫn tính** vào hạn mức 50 câu/ngày.
>
> Hạn mức theo ngày được tính theo múi giờ `Asia/Ho_Chi_Minh` (UTC+7), reset lúc 00:00 giờ Việt Nam.

**Object `AISource`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `chunk_id` | `string (UUID)` | ID đoạn transcript trong bảng `lesson_chunks` (dùng khi FE cần debug hoặc BE đối soát) |
| `text` | `string` | Đoạn transcript được trích dẫn |
| `start_time` | `float` | Thời điểm bắt đầu (giây) |
| `end_time` | `float` | Thời điểm kết thúc |
| `relevance_score` | `float` | Điểm liên quan (0.0–1.0, optional) |

> 📌 Đây là định nghĩa JSON gốc duy nhất cho `sources`; mọi endpoint trả `sources` (4.1 ask, 4.2 chat-history, phụ lục thống kê) đều dùng cấu trúc này.

**Response Headers bổ sung:**

| Header | Kiểu | Mô tả |
|--------|------|-------|
| `X-AI-Questions-Remaining` | `int` | Số lượt hỏi còn lại |
| `X-AI-Daily-Limit` | `int` | Tổng giới hạn/ngày |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `QUESTION_TOO_SHORT` | Câu hỏi < 5 ký tự | Inline error |
| `403` | `NOT_ENROLLED` | Chưa mua khóa | Toast: "Vui lòng mua khóa học" |
| `429` | `AI_QUOTA_EXCEEDED` | Hết lượt hỏi AI hôm nay | Banner: "Bạn đã sử dụng hết lượt hỏi AI hôm nay" |
| `504` | `AI_TIMEOUT` | AI xử lý quá lâu (> 30s) | Bubble lỗi: "AI đang gặp sự cố" + nút "Thử lại" |

---

### 4.2 Lấy lịch sử chat AI

| # | Hành động | Endpoint |
|---|-----------|----------|
| 4.2 | Tải lịch sử chat cho 1 bài giảng | `GET /api/lessons/{lesson_id}/chat-history` |

**FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `page` | `int` | ❌ | Default: `1` |
| `page_size` | `int` | ❌ | Default: `50` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `array[ChatMessage]` | Danh sách tin nhắn, sort `created_at` asc |
| `total` | `int` | Tổng số tin nhắn |

**Object `ChatMessage`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `role` | `string` | `enum("user", "ai")` |
| `content` | `string` | Nội dung tin nhắn |
| `sources` | `array[AISource]?` | Nguồn trích dẫn (chỉ có khi `role = ai`) |
| `created_at` | `string (ISO 8601)` | Thời điểm gửi |

---

### 4.3 Lấy câu hỏi gợi ý

| # | Hành động | Endpoint |
|---|-----------|----------|
| 4.3 | Lấy chip gợi ý câu hỏi cho bài giảng | `GET /api/lessons/{lesson_id}/suggested-questions` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `array[string]` | 3–4 câu hỏi gợi ý |

---

### 4.4 Gửi phản hồi chất lượng câu trả lời AI

| # | Hành động | Endpoint |
|---|-----------|----------|
| 4.4 | Học viên đánh giá 👍/👎 câu trả lời AI | `POST /api/ai-messages/{message_id}/feedback` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `feedback` | `string` | ✅ | `enum("up", "down")` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message_id` | `string (UUID)` | PK tin nhắn AI |
| `feedback` | `string` | Giá trị đã ghi nhận |
| `message` | `string` | `"Cảm ơn phản hồi của bạn."` |

> 📌 Phản hồi được lưu vào bảng `ai_qa_logs` (cột `feedback`) và chỉ dùng cho thống kê chất lượng (mục A-17), không dùng để huấn luyện lại mô hình trong phạm vi Đồ án 1.

**Mã lỗi:** `400 VALIDATION_ERROR`, `404 NOT_FOUND` (tin nhắn không tồn tại hoặc không thuộc học viên hiện tại).

---

## 5. AI TÓM TẮT BÀI GIẢNG

> Màn hình: `M-14`

---

### 5.1 Tạo bản tóm tắt bài giảng

| # | Hành động | Endpoint |
|---|-----------|----------|
| 5.1 | Yêu cầu AI tóm tắt bài giảng | `POST /api/lessons/{lesson_id}/summarize` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `scope` | `string` | ❌ | `enum("full", "chapter")`. Default: `"full"` |
| `chapter_id` | `string (UUID)` | ❌ | Bắt buộc nếu `scope = "chapter"` |
| `force_regenerate` | `boolean` | ❌ | `true` để bypass cache server-side. Default: `false` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `summary` | `string` | Bản tóm tắt (Markdown format, bullet points) |
| `key_timestamps` | `array[KeyTimestamp]` | Mốc thời gian đáng chú ý |
| `is_cached` | `boolean` | `true` nếu trả từ cache |
| `generated_at` | `string (ISO 8601)` | Thời điểm tạo bản tóm tắt |

**Object `KeyTimestamp`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `label` | `string` | Mô tả ngắn nội dung tại mốc |
| `start_time` | `float` | Thời điểm (giây) |
| `end_time` | `float` | Thời điểm kết thúc |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `TRANSCRIPT_TOO_SHORT` | Nội dung quá ngắn để tóm tắt | Text: "Nội dung bài giảng quá ngắn để tóm tắt." |
| `429` | `AI_QUOTA_EXCEEDED` | Hết lượt sử dụng AI | Banner warning |
| `504` | `AI_TIMEOUT` | Timeout tạo tóm tắt | Card lỗi + nút "Thử lại" |

---

## 6. QUIZ & BÀI TẬP

> Màn hình: `M-17`, `M-18`, `M-19`, `A-09`, `A-10`, `A-11`

---

### 6.1 Lấy câu hỏi quiz giữa video

| # | Hành động | Endpoint |
|---|-----------|----------|
| 6.1 | Tải câu hỏi quiz khi trigger tại mốc thời gian | `GET /api/quizzes/{quiz_id}` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK quiz |
| `questions` | `array[QuizQuestion]` | Danh sách câu hỏi (có thể > 1 tại cùng mốc) |
| `total_questions` | `int` | Tổng số câu |

**Object `QuizQuestion`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK câu hỏi |
| `type` | `string` | `enum("single_choice", "true_false")` — M-17 hỗ trợ 2 loại câu hỏi này |
| `content` | `string` | Nội dung câu hỏi |
| `options` | `array[QuizOption]` | Phương án (2 phương án A/B cho `true_false`, 4 phương án A/B/C/D cho `single_choice`) |
| `order` | `int` | Thứ tự hiển thị (1, 2, 3...) |

**Object `QuizOption`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `key` | `string` | `enum("A", "B", "C", "D")` |
| `content` | `string` | Nội dung phương án |

---

### 6.2 Nộp câu trả lời quiz

| # | Hành động | Endpoint |
|---|-----------|----------|
| 6.2 | Gửi đáp án quiz giữa video | `POST /api/quiz-responses` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `quiz_id` | `string (UUID)` | ✅ | FK quiz |
| `question_id` | `string (UUID)` | ✅ | FK câu hỏi |
| `answer` | `string` | ✅ | `enum("A", "B", "C", "D")` (với `true_false` gửi `"A"` hoặc `"B"`) |
| `time_taken` | `int` | ❌ | Thời gian trả lời (giây) |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `correct` | `boolean` | Đúng hay sai |
| `correct_answer` | `string` | Đáp án đúng (`"A"`, `"B"`, `"C"`, `"D"`) |
| `explanation` | `string?` | Giải thích (nullable) |

---

### 6.3 Lấy bài tập cuối bài

| # | Hành động | Endpoint |
|---|-----------|----------|
| 6.3 | Tải bài tập cuối bài giảng | `GET /api/exercises/{exercise_id}` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK bài tập |
| `title` | `string` | Tên bài tập |
| `lesson_id` | `string (UUID)` | FK bài giảng |
| `time_limit` | `int` | Thời gian (giây), `0` = không giới hạn |
| `passing_score` | `int` | Điểm đạt (%) |
| `max_attempts` | `int` | Số lần làm tối đa, `0` = không giới hạn |
| `attempts_used` | `int` | Số lần đã làm |
| `questions` | `array[ExerciseQuestion]` | Danh sách câu hỏi |
| `total_questions` | `int` | Tổng số câu |

**Object `ExerciseQuestion`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `type` | `string` | `enum("single_choice", "multiple_choice", "true_false", "essay")` — theo chuẩn `09` §4.1 |
| `content` | `string` | Nội dung câu hỏi |
| `options` | `array[QuizOption]?` | Phương án (chỉ có khi `type` thuộc `single_choice`, `multiple_choice`, `true_false`) |
| `order` | `int` | Thứ tự |

---

### 6.4 Nộp bài tập

| # | Hành động | Endpoint |
|---|-----------|----------|
| 6.4 | Nộp bài tập cuối bài | `POST /api/exercises/{exercise_id}/submit` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `answers` | `array[ExerciseAnswer]` | ✅ | Danh sách câu trả lời |
| `time_spent` | `int` | ❌ | Tổng thời gian làm bài (giây) |

**Object `ExerciseAnswer`:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `question_id` | `string (UUID)` | ✅ | FK câu hỏi |
| `answer` | `string` | ✅ | Đáp án: key/danh sách key phương án (`"A"/"B"/"C"/"D"` hoặc `"TRUE"/"FALSE"`), hoặc text tự luận (10–5000 ký tự) |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `submission_id` | `string (UUID)` | PK bài nộp |
| `score` | `float?` | Điểm % (nullable nếu có câu tự luận chưa chấm) |
| `passed` | `boolean?` | Đạt/không đạt (nullable nếu chờ chấm) |
| `status` | `string` | `enum("graded", "pending_grading")` — theo chuẩn `09` §4.1 (`pending_grading` khi có câu tự luận chờ chấm) |
| `attempts_remaining` | `int` | Số lần làm lại còn lại |
| `details` | `array[AnswerResult]?` | Chi tiết từng câu (chỉ khi `status = graded`) |

**Object `AnswerResult`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `question_id` | `string (UUID)` | FK câu hỏi |
| `correct` | `boolean?` | Đúng/sai (nullable nếu tự luận) |
| `correct_answer` | `string?` | Đáp án đúng (trắc nghiệm only) |
| `explanation` | `string?` | Giải thích |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `INCOMPLETE_ANSWERS` | Thiếu câu trả lời | Inline error |
| `403` | `MAX_ATTEMPTS_REACHED` | Hết lần làm | "Đã hết số lần làm bài" |
| `409` | `ALREADY_SUBMITTED` | Đã nộp bài rồi (trùng) | Navigate đến kết quả |

---

### 6.5 Quản lý ngân hàng câu hỏi (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 6.5a | Danh sách câu hỏi | `GET /api/admin/questions` |
| 6.5b | Tạo câu hỏi | `POST /api/admin/questions` |
| 6.5c | Sửa câu hỏi | `PUT /api/admin/questions/{question_id}` |
| 6.5d | Xóa câu hỏi | `DELETE /api/admin/questions/{question_id}` |

**6.5a — Query Params:**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `page`, `page_size` | `int` | ❌ | Phân trang |
| `type` | `string` | ❌ | `enum("single_choice", "multiple_choice", "true_false", "essay")` |
| `difficulty` | `string` | ❌ | `enum("easy", "medium", "hard")` |
| `lesson_id` | `string (UUID)` | ❌ | Lọc theo bài giảng |
| `search` | `string` | ❌ | Tìm trong nội dung câu hỏi |

**6.5b — FE gửi lên (Tạo câu hỏi):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `type` | `string` | ✅ | `enum("single_choice", "multiple_choice", "true_false", "essay")` |
| `content` | `string` | ✅ | Nội dung, 10–2000 ký tự |
| `options` | `array[{key: string, content: string}]?` | ✅ (TN) | Phương án trả lời (bắt buộc với `single_choice`, `multiple_choice`, `true_false`; tự luận không gửi) |
| `correct_answer` | `string?` | ✅ (TN) | Đáp án đúng: key phương án (`"A"`, `"B"`,...) hoặc mảng JSON nếu nhiều đáp án; `"TRUE"/"FALSE"` với đúng sai; tự luận để `null` |
| `explanation` | `string` | ❌ | Giải thích, max 2000 ký tự (chỉ trả cho học viên sau khi nộp bài theo BR-13) |
| `difficulty` | `string` | ✅ | `enum("easy", "medium", "hard")` |
| `lesson_id` | `string (UUID)` | ❌ | FK bài giảng liên quan |

**6.5d — Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `409` | `QUESTION_IN_USE` | Câu hỏi đang sử dụng trong bộ đề | Modal cảnh báo |

---

### 6.6 Tạo bộ đề thi / Quiz (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 6.6a | Tạo bộ đề | `POST /api/admin/exams` |
| 6.6b | Sửa bộ đề | `PUT /api/admin/exams/{exam_id}` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `title` | `string` | ✅ | Tên đề, 5–200 ký tự |
| `lesson_id` | `string (UUID)` | ❌ | FK bài giảng liên quan (bắt buộc khi `exam_type` thuộc `in_video_quiz`, `end_lesson_exam`) |
| `course_id` | `string (UUID)` | ❌ | FK khóa học liên quan (bắt buộc khi `exam_type = "end_course_exam"`) |
| `exam_type` | `string` | ✅ | `enum("in_video_quiz", "end_lesson_exam", "end_course_exam")`. Default: `"end_lesson_exam"` |
| `trigger_timestamp` | `float?` | ❌ | Mốc giây video tự dừng và bật quiz (bắt buộc khi `exam_type = "in_video_quiz"` theo `09` §5.5) |
| `time_limit` | `int` | ❌ | Thời gian giới hạn (phút), `0` = không giới hạn (`duration_minutes` trong DB) |
| `passing_score` | `int` | ✅ | Điểm đạt (0–100 %) |
| `max_attempts` | `int` | ✅ | Số lần làm (0 = không giới hạn) |
| `question_ids` | `array[string (UUID)]` | ✅ | Danh sách FK câu hỏi đã chọn |

---

## 7. GHI CHÚ THEO MỐC THỜI GIAN

> Màn hình: `M-15`, `M-16`

---

### 7.1 Lấy danh sách ghi chú

| # | Hành động | Endpoint |
|---|-----------|----------|
| 7.1 | Xem ghi chú của 1 bài giảng | `GET /api/lessons/{lesson_id}/notes` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `array[Note]` | Danh sách ghi chú, sort theo `timestamp` asc |

**Object `Note`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `content` | `string` | Nội dung ghi chú |
| `timestamp` | `float` | Mốc thời gian video (giây) |
| `created_at` | `string (ISO 8601)` | Thời điểm tạo |
| `updated_at` | `string (ISO 8601)` | Thời điểm cập nhật |

---

### 7.2 Tạo ghi chú

| # | Hành động | Endpoint |
|---|-----------|----------|
| 7.2 | Tạo ghi chú tại mốc thời gian | `POST /api/lessons/{lesson_id}/notes` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `content` | `string` | ✅ | Nội dung, 1–2000 ký tự |
| `timestamp` | `float` | ✅ | Mốc thời gian video hiện tại (giây) |

**BE trả về (Response 201):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK ghi chú mới |
| `content` | `string` | Nội dung |
| `timestamp` | `float` | Mốc thời gian |
| `created_at` | `string (ISO 8601)` | Thời điểm tạo |

---

### 7.3 Sửa ghi chú

| # | Hành động | Endpoint |
|---|-----------|----------|
| 7.3 | Cập nhật nội dung ghi chú | `PUT /api/notes/{note_id}` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `content` | `string` | ✅ | Nội dung mới, 1–2000 ký tự |

**BE trả về (Response 200):** Object `Note` đầy đủ sau cập nhật.

---

### 7.4 Xóa ghi chú

| # | Hành động | Endpoint |
|---|-----------|----------|
| 7.4 | Xóa ghi chú | `DELETE /api/notes/{note_id}` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Đã xóa ghi chú."` |

---

## 8. THANH TOÁN (PayOS / VietQR)

> Màn hình: `M-10`, `M-11`

---

### 8.1 Tạo đơn hàng thanh toán

| # | Hành động | Endpoint |
|---|-----------|----------|
| 8.1 | Tạo đơn hàng + lấy QR thanh toán | `POST /api/orders` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `course_id` | `string (UUID)` | ✅ | FK khóa học cần mua |

**BE trả về (Response 201):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `order_id` | `string (UUID)` | PK đơn hàng |
| `order_code` | `string` | Mã đơn hàng hiển thị |
| `amount` | `int` | Số tiền (VND) |
| `course_title` | `string` | Tên khóa học |
| `qr_code_url` | `string` | URL ảnh QR VietQR |
| `payment_url` | `string?` | URL thanh toán PayOS (nếu dùng redirect) |
| `expires_at` | `string (ISO 8601)` | Thời điểm hết hạn QR (thường +15 phút) |
| `status` | `string` | `"pending"` |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `ALREADY_ENROLLED` | Đã mua khóa học này rồi | Toast: "Bạn đã sở hữu khóa học này" |
| `502` | `PAYMENT_GATEWAY_ERROR` | PayOS không phản hồi | Card lỗi: "Không thể tạo mã thanh toán" + nút "Thử lại" |

---

### 8.2 Kiểm tra trạng thái thanh toán (Polling)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 8.2 | Polling kiểm tra trạng thái giao dịch | `GET /api/orders/{order_id}/status` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `order_id` | `string (UUID)` | PK |
| `status` | `string` | `enum("pending", "paid", "failed", "cancelled", "expired")` |
| `paid_at` | `string? (ISO 8601)` | Thời điểm thanh toán (nullable) |
| `transaction_id` | `string?` | Mã giao dịch ngân hàng (nullable) |
| `failure_reason` | `string?` | Lý do thất bại (nullable) |

> ⚠️ FE polling mỗi 3 giây. Dừng khi `status ∈ {paid, failed, cancelled, expired}`.

---

### 8.3 Hủy đơn hàng

| # | Hành động | Endpoint |
|---|-----------|----------|
| 8.3 | Hủy thanh toán | `PUT /api/orders/{order_id}/cancel` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `order_id` | `string (UUID)` | PK |
| `status` | `string` | `"cancelled"` |
| `message` | `string` | `"Đơn hàng đã được hủy."` |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `ORDER_ALREADY_PAID` | Đơn đã thanh toán, không thể hủy | Toast: "Đơn hàng đã được thanh toán" |
| `400` | `ORDER_ALREADY_CANCELLED` | Đã hủy rồi | Ignore / navigate back |

---

### 8.4 Webhook xác nhận thanh toán (PayOS → Backend)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 8.4 | PayOS gọi webhook báo kết quả giao dịch | `POST /api/webhooks/payos` |

> ⚠️ Endpoint server-to-server, **không dùng JWT**. Xác thực bằng chữ ký HMAC từ PayOS kiểm tra ở tầng middleware. Lưu ý FE Mobile **không gọi** endpoint này.

**PayOS gửi lên (Request Body):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `order_code` | `string` | ✅ | Mã đơn hàng PayOS |
| `status` | `string` | ✅ | `enum("PAID", "FAILED", "CANCELLED")` |
| `transaction_id` | `string` | ❌ | Mã giao dịch ngân hàng |
| `signature` | `string` | ✅ | Chữ ký HMAC để kiểm tra tính xác thực |

**BE trả về (Response 200):** `{ "received": true }` — luôn trả 200 sau khi ghi nhận sự kiện, kể cả sự kiện trùng lặp.

**Quy tắc xử lý bắt buộc:**

- **Idempotency:** Cùng một `order_code` gọi nhiều lần chỉ được cập nhật một lần; xử lý trùng lặp trả 200 không làm thay đổi dữ liệu (bảo vệ bởi ràng buộc duy nhất trạng thái trong DB).
- **Nguyên tử:** Ghi nhận trạng thái `paid` và tạo bản ghi ghi danh (enrollment) phải trong **cùng một giao dịch** database; nếu tạo ghi danh thất bại thì rollback cả hai và sự kiện sẽ được xử lý lại.
- Đơn chỉ được chuyển `paid` nếu đang ở trạng thái `pending` và chưa quá `expires_at`.

---

## 9. UPLOAD & PIPELINE XỬ LÝ VIDEO (Admin)

> Màn hình: `A-06`, `A-07`, `A-08`

---

### 9.1 Giao thức tải lên video trực tiếp qua Presigned URL (Client Direct Upload)

> 📌 **Quy tắc kiến trúc từ `11` §3.3.1 & `10` §3.3:**  
> Backend **tuyệt đối không trung chuyển** dữ liệu binary video để tránh nghẽn I/O server. Trình duyệt Web Admin tải từng chunk **trực tiếp lên Amazon S3** thông qua URL có chữ ký (Presigned URL) do Backend cấp; Backend chỉ quản lý metadata, session multipart và trạng thái pipeline.

| # | Hành động | Endpoint |
|---|-----------|----------|
| 9.1a | Khởi tạo phiên tải lên nhiều phần | `POST /api/admin/videos/upload/init` |
| 9.1b | Lấy Presigned URL cho từng phần | `POST /api/admin/videos/upload` |
| 9.1c | Hoàn tất tải lên & kích hoạt pipeline | `POST /api/admin/videos/upload/complete` |

**Ràng buộc kỹ thuật (khớp `09` §5.5 & `11` §3.3.1):**
- Dung lượng mỗi part: tối thiểu **5MB** (riêng part cuối được nhỏ hơn), tối đa **200MB** (`upload_max_part_bytes`). Kích thước part khuyến nghị: **50MB**.
- Dung lượng video tối đa: **5GB** (`upload_max_total_bytes`). Vượt quá trả `413 FILE_TOO_LARGE`.
- Định dạng tệp: MP4, MOV, AVI, MKV, WEBM (`400 INVALID_FILE_FORMAT`).
- Presigned URL có thời hạn ngắn; hết hạn thì FE xin lại URL cho part đó chứ không làm hỏng phiên tải lên. Khi mất mạng, FE gọi lại 9.1a để nhận danh sách `parts_uploaded` và tiếp tục các phần còn thiếu.

---

#### 9.1a Khởi tạo phiên tải lên (`POST /api/admin/videos/upload/init`)

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `lesson_id` | `string (UUID)` | ✅ | FK bài giảng cần gắn video |
| `file_name` | `string` | ✅ | Tên file gốc (VD: `"bai_01_intro.mp4"`) |
| `file_size` | `int` | ✅ | Kích thước toàn bộ file (bytes), max 5GB |
| `content_type` | `string` | ✅ | MIME type (VD: `"video/mp4"`, `"video/quicktime"`) |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `video_id` | `string (UUID)` | PK video (được tạo ở trạng thái `uploading`) |
| `upload_id` | `string` | Amazon S3 Multipart Upload ID |
| `part_size` | `int` | Kích thước khuyến nghị mỗi phần (bytes, mặc định 52.428.800 = 50MB) |
| `total_parts` | `int` | Tổng số phần cần chia và tải lên |
| `parts_uploaded` | `array[int]` | Danh sách số thứ tự phần đã tải thành công (rỗng nếu phiên mới, có dữ liệu nếu tiếp tục khi mất mạng) |

---

#### 9.1b Lấy Presigned URL cho từng phần (`POST /api/admin/videos/upload`)

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `video_id` | `string (UUID)` | ✅ | PK video |
| `upload_id` | `string` | ✅ | Multipart Upload ID nhận từ bước 9.1a |
| `part_number` | `int` | ✅ | Số thứ tự phần (bắt đầu từ `1` đến `total_parts`) |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `presigned_url` | `string` | URL ký trước của Amazon S3 để FE gửi HTTP `PUT` trực tiếp |
| `expires_at` | `string (ISO 8601)` | Thời điểm hết hạn của presigned URL |

> 🌐 **Thao tác Client trực tiếp với Amazon S3:**  
> FE thực hiện `PUT <presigned_url>` với body là binary chunk của part tương ứng.  
> Amazon S3 trả về HTTP `200 OK` kèm header `ETag: "<etag_value>"`.  
> FE lưu lại cặp `{ "part_number": part_number, "etag": "<etag_value>" }` để dùng cho bước 9.1c.

---

#### 9.1c Hoàn tất tải lên & kích hoạt pipeline (`POST /api/admin/videos/upload/complete`)

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `video_id` | `string (UUID)` | ✅ | PK video |
| `upload_id` | `string` | ✅ | Multipart Upload ID |
| `parts` | `array[UploadPart]` | ✅ | Danh sách đầy đủ các phần đã tải lên |

**Object `UploadPart`:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `part_number` | `int` | ✅ | Số thứ tự phần (`1` .. `total_parts`) |
| `etag` | `string` | ✅ | Giá trị ETag nhận được từ header response của Amazon S3 |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `video_id` | `string (UUID)` | PK video |
| `overall_status` | `string` | Trạng thái chuyển sang `"uploaded"` và worker bắt đầu bước `"transcode"` |
| `message` | `string` | `"Tải lên video hoàn tất, đã đưa vào pipeline xử lý."` |

**Mã lỗi nhóm 9.1:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `INVALID_FILE_FORMAT` | Định dạng không hỗ trợ (không thuộc MP4/MOV/AVI/MKV/WEBM) | Inline: "File không hợp lệ: [lý do]" |
| `404` | `LESSON_NOT_FOUND` | Bài giảng không tồn tại | Toast: "Bài giảng không tồn tại" |
| `409` | `UPLOAD_IN_PROGRESS` | Video của bài giảng này đang trong tiến trình xử lý | Modal cảnh báo |
| `413` | `FILE_TOO_LARGE` | Vượt quá 5GB hoặc kích thước part vượt quá 200MB | Inline: "File quá lớn (tối đa 5GB)" |

---

### 9.2 Lấy trạng thái pipeline xử lý

| # | Hành động | Endpoint |
|---|-----------|----------|
| 9.2 | Kiểm tra pipeline status | `GET /api/admin/pipeline/{video_id}/status` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `video_id` | `string (UUID)` | PK video |
| `lesson_id` | `string (UUID)` | FK bài giảng |
| `lesson_title` | `string` | Tên bài giảng |
| `steps` | `array[PipelineStep]` | Chi tiết từng bước pipeline |
| `overall_status` | `string` | `enum("uploading", "uploaded", "processing", "completed", "failed")` |
| `error_message` | `string?` | Chi tiết lỗi nếu failed |
| `started_at` | `string? (ISO 8601)` | Thời điểm bắt đầu xử lý |
| `completed_at` | `string? (ISO 8601)` | Thời điểm hoàn tất |

**Object `PipelineStep`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `step` | `string` | `enum("upload", "transcode", "transcribe", "index")` — 4 bước, tương ứng `Uploading → Processing_HLS → Processing_STT → Processing_Indexing` trong tài liệu `00` |
| `status` | `string` | `enum("pending", "processing", "completed", "failed")` |
| `progress` | `float?` | % hoàn thành (0.0–100.0, nullable) |
| `error_message` | `string?` | Chi tiết lỗi (nullable) |
| `started_at` | `string? (ISO 8601)` | Thời điểm bắt đầu |
| `completed_at` | `string? (ISO 8601)` | Thời điểm hoàn tất |

> 📌 Ánh xạ tên tương thích: phiên bản hợp đồng trước đây gọi bước phiên âm là `"stt"`. Backend chấp nhận cả `"stt"` (đọc) và trả về tên mới `"transcribe"`; FE mới nên dùng `"transcribe"`.

---

### 9.3 Danh sách pipeline (Admin Dashboard)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 9.3 | Danh sách video + trạng thái pipeline | `GET /api/admin/pipeline` |

**FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `page`, `page_size` | `int` | ❌ | Phân trang |
| `status` | `string` | ❌ | Filter theo overall_status |

**BE trả về:** Paginated list of `PipelineStatus` objects (giống 9.2 nhưng dạng danh sách).

---

### 9.4 Xử lý lại pipeline step

| # | Hành động | Endpoint |
|---|-----------|----------|
| 9.4 | Retry 1 bước pipeline cụ thể | `POST /api/admin/pipeline/{video_id}/retry` |

**FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `step` | `string` | ✅ | `enum("upload", "transcode", "transcribe", "index")` — bước cần retry. Chấp nhận giá trị cũ `"stt"` tương đương `"transcribe"` |

> 📌 Hành vi retry theo từng bước: `upload` — tải lại từ đầu và giữ tệp thô hiện có; `transcode` — chạy lại từ tệp thô, không mất dữ liệu; `transcribe` — chạy lại từ tệp âm thanh đã trích xuất (hoặc trích xuất lại nếu thiếu); `index` — chạy lại từ transcript hiện hành, không chạy lại phiên âm.

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Đã bắt đầu xử lý lại bước [step]."` |
| `video_id` | `string (UUID)` | PK video |

---

### 9.5 Hủy pipeline

| # | Hành động | Endpoint |
|---|-----------|----------|
| 9.5 | Hủy xử lý pipeline | `PUT /api/admin/pipeline/{video_id}/cancel` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Đã hủy xử lý."` |
| `overall_status` | `string` | `"uploaded"` (revert) |

---

### 9.6 Quản lý Transcript (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 9.6a | Lấy transcript | `GET /api/admin/lessons/{lesson_id}/transcript` |
| 9.6b | Cập nhật transcript | `PUT /api/admin/transcripts/{transcript_id}` |

**9.6a — BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `transcript_id` | `string (UUID)` | PK transcript |
| `lesson_id` | `string (UUID)` | FK bài giảng |
| `segments` | `array[TranscriptSegment]` | Danh sách dòng transcript |
| `hls_stream_url` | `string` | URL video preview |

**9.6b — FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `segments` | `array[TranscriptEditSegment]` | ✅ | Toàn bộ danh sách segment sau chỉnh sửa |

**Object `TranscriptEditSegment`:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `start` | `float` | ✅ | Thời điểm bắt đầu (giây) |
| `end` | `float` | ✅ | Thời điểm kết thúc |
| `text` | `string` | ✅ | Nội dung (1–1000 ký tự) |

**9.6b — BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"Transcript đã cập nhật."` |
| `reindexing_triggered` | `boolean` | `true` nếu text thay đổi → vector re-indexing tự động chạy |

---

## 10. THÔNG BÁO

> Màn hình: `M-06` (badge), `M-26`

---

### 10.1 Lấy số thông báo chưa đọc

| # | Hành động | Endpoint |
|---|-----------|----------|
| 10.1 | Lấy badge count | `GET /api/notifications/unread-count` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `count` | `int` | Số thông báo chưa đọc |

---

### 10.2 Lấy danh sách thông báo

| # | Hành động | Endpoint |
|---|-----------|----------|
| 10.2 | Xem danh sách thông báo | `GET /api/notifications` |

**FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `page`, `page_size` | `int` | ❌ | Phân trang |

**Object `Notification`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `title` | `string` | Tiêu đề |
| `body` | `string` | Nội dung |
| `type` | `string` | `enum("payment", "course", "system", "exercise")` |
| `is_read` | `boolean` | Đã đọc chưa |
| `action_url` | `string?` | Deep link / route cần navigate (nullable) |
| `created_at` | `string (ISO 8601)` | Thời điểm tạo |

---

### 10.3 Đánh dấu đã đọc

| # | Hành động | Endpoint |
|---|-----------|----------|
| 10.3 | Đánh dấu thông báo đã đọc | `PUT /api/notifications/{notification_id}/read` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | `"OK"` |

---

## 11. HỒ SƠ CÁ NHÂN

> Màn hình: `M-23`

---

### 11.1 Lấy thông tin hồ sơ

| # | Hành động | Endpoint |
|---|-----------|----------|
| 11.1 | Xem hồ sơ cá nhân | `GET /api/users/me` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `full_name` | `string` | Họ tên |
| `email` | `string` | Email |
| `avatar_url` | `string?` | URL ảnh đại diện |
| `role` | `string` | `enum("student", "admin")` |
| `created_at` | `string (ISO 8601)` | Ngày tạo tài khoản |

---

### 11.2 Cập nhật hồ sơ

| # | Hành động | Endpoint |
|---|-----------|----------|
| 11.2 | Cập nhật thông tin cá nhân | `PUT /api/users/me` |

**FE gửi lên (`multipart/form-data`):**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `full_name` | `string` | ❌ | 2–100 ký tự |
| `avatar` | `file` | ❌ | JPEG/PNG/WebP, max 2MB |

**BE trả về (Response 200):** Object user đầy đủ sau cập nhật.

---

### 11.3 Đổi mật khẩu

| # | Hành động | Endpoint |
|---|-----------|----------|
| 11.3 | Đổi mật khẩu trong app | `PUT /api/users/me/password` |

**FE gửi lên:**

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `current_password` | `string` | ✅ | Mật khẩu hiện tại |
| `new_password` | `string` | ✅ | Mật khẩu mới (cùng quy tắc đăng ký) |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `WRONG_CURRENT_PASSWORD` | Mật khẩu hiện tại sai | Inline error |
| `400` | `PASSWORD_TOO_WEAK` | Mật khẩu mới quá yếu | Inline error |
| `400` | `SAME_AS_OLD_PASSWORD` | MK mới trùng MK cũ | Inline error |

---

### 11.4 Quản lý học viên (Admin)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 11.4a | Lấy danh sách học viên | `GET /api/admin/users` |
| 11.4b | Khóa tài khoản học viên | `PUT /api/admin/users/{user_id}/lock` |
| 11.4c | Mở khóa tài khoản học viên | `PUT /api/admin/users/{user_id}/unlock` |

**11.4a — FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `page`, `page_size` | `int` | ❌ | Phân trang |
| `search` | `string` | ❌ | Tìm theo tên hoặc email |
| `status` | `string` | ❌ | `enum("active", "locked", "unverified")` |

**11.4a — BE trả về:** Paginated list of `AdminUser` objects.

**Object `AdminUser`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK người dùng |
| `full_name` | `string` | Họ tên |
| `email` | `string` | Email |
| `avatar_url` | `string?` | Ảnh đại diện |
| `role` | `string` | `enum("student", "admin")` |
| `is_verified` | `boolean` | Đã xác thực email hay chưa |
| `is_locked` | `boolean` | Tài khoản có đang bị khóa hay không |
| `enrolled_courses_count` | `int` | Số khóa đã ghi danh |
| `created_at` | `string (ISO 8601)` | Ngày tạo tài khoản |

**11.4b / 11.4c — BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `message` | `string` | Kết quả khóa / mở khóa |
| `user_id` | `string (UUID)` | Người dùng vừa cập nhật |
| `is_locked` | `boolean` | Trạng thái sau cập nhật |

**Mã lỗi:** `403 FORBIDDEN`, `404 NOT_FOUND`, `409 CANNOT_LOCK_ADMIN_SELF`.

---

## 12. BÁO CÁO & THỐNG KÊ (Admin)

> Màn hình: `A-02`, `A-15`, `A-16`, `A-17`

---

### 12.1 Dashboard tổng quan (KPI)

| # | Hành động | Endpoint |
|---|-----------|----------|
| 12.1 | Lấy KPI tổng quan | `GET /api/admin/dashboard` |

**FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `time_range` | `string` | ❌ | `enum("day", "week", "month")`. Default: `"month"` |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `revenue` | `KPICard` | Doanh thu |
| `students` | `KPICard` | Học viên |
| `ai_questions` | `KPICard` | Câu hỏi AI |
| `video_pipeline` | `KPICard` | Video pipeline |
| `revenue_chart` | `array[ChartPoint]` | Dữ liệu biểu đồ xu hướng doanh thu |
| `pipeline_table` | `array[PipelineRow]` | Bảng video đang xử lý |

**Object `KPICard`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `value` | `int / float` | Giá trị hiện tại |
| `previous_value` | `int / float` | Giá trị kỳ trước |
| `change_percent` | `float` | % thay đổi so với kỳ trước |
| `trend` | `string` | `enum("up", "down", "stable")` |

**Object `ChartPoint`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `date` | `string (YYYY-MM-DD)` | Ngày |
| `value` | `float` | Giá trị |

---

### 12.2 Báo cáo doanh thu chi tiết

| # | Hành động | Endpoint |
|---|-----------|----------|
| 12.2a | Lấy KPI doanh thu | `GET /api/admin/revenue/summary` |
| 12.2b | Lấy biểu đồ doanh thu | `GET /api/admin/revenue/chart` |
| 12.2c | Lấy danh sách giao dịch | `GET /api/admin/revenue/transactions` |

**12.2a, 12.2b, 12.2c — Query Params chung:**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `date_from` | `string (YYYY-MM-DD)` | ❌ | Ngày bắt đầu (default: 30 ngày trước) |
| `date_to` | `string (YYYY-MM-DD)` | ❌ | Ngày kết thúc (default: hôm nay) |

**12.2a — BE trả về:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `total_revenue` | `int` | Tổng doanh thu (VND) trong khoảng |
| `monthly_revenue` | `int` | Doanh thu tháng hiện tại |
| `successful_transactions` | `int` | Số giao dịch thành công |
| `failed_transactions` | `int` | Số giao dịch thất bại |

**12.2c — Object `Transaction`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `order_code` | `string` | Mã đơn hàng |
| `student_name` | `string` | Tên học viên |
| `student_email` | `string` | Email học viên |
| `course_title` | `string` | Tên khóa học |
| `amount` | `int` | Số tiền (VND) |
| `status` | `string` | `enum("paid", "pending", "failed", "cancelled", "expired")` |
| `payment_method` | `string` | Phương thức TT |
| `paid_at` | `string? (ISO 8601)` | Thời điểm thanh toán |
| `created_at` | `string (ISO 8601)` | Thời điểm tạo đơn |

---

### 12.3 Báo cáo phân tích hành vi học viên

| # | Hành động | Endpoint |
|---|-----------|----------|
| 12.3 | Lấy dữ liệu phân tích hành vi | `GET /api/admin/analytics/students` |

**FE gửi lên (Query Params):**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `date_from` | `string (YYYY-MM-DD)` | ❌ | Ngày bắt đầu |
| `date_to` | `string (YYYY-MM-DD)` | ❌ | Ngày kết thúc |
| `course_id` | `string (UUID)` | ❌ | Lọc theo khóa học |

> Phạm vi MVP: các chỉ số được tính từ `enrollments`, `lesson_progress` và `exercise_attempts`. Các chỉ số yêu cầu sự kiện xem chi tiết liên tục như lượt xem chính xác, tỷ lệ bỏ dở theo thời gian thực và retention nâng cao chỉ khả dụng khi bật telemetry học tập; nếu chưa bật telemetry, Backend trả mảng rỗng cho các trường nâng cao thay vì suy đoán.

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `completion_rate` | `array[{course_title: string, rate: float}]` | Tỷ lệ hoàn thành theo khóa (bar chart) |
| `avg_watch_duration` | `array[{course_title: string, minutes: float}]` | Thời lượng xem TB theo khóa (horizontal bar) |
| `top_lessons` | `array[{lesson_title: string, views: int, course_title: string}]` | Top bài giảng được xem nhiều nhất |
| `high_dropout_lessons` | `array[DropoutLesson]` | Bài giảng có tỷ lệ bỏ dở cao |
| `daily_study_time` | `array[{date: string, hours: float}]` | Thời gian học theo ngày (line chart) |
| `retention_rate` | `float` | Tỷ lệ quay lại học (%) |

**Object `DropoutLesson`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `lesson_id` | `string (UUID)` | FK bài giảng |
| `lesson_title` | `string` | Tên bài |
| `course_title` | `string` | Tên khóa |
| `dropout_rate` | `float` | Tỷ lệ bỏ dở (%) |
| `avg_watch_percent` | `float` | % xem trung bình |

---

### 12.4 Thống kê câu hỏi AI

| # | Hành động | Endpoint |
|---|-----------|----------|
| 12.4a | Lấy KPI + biểu đồ AI | `GET /api/admin/analytics/ai-questions` |
| 12.4b | Lấy danh sách câu hỏi phổ biến | `GET /api/admin/analytics/ai-questions/top` |

**12.4a — Query Params:**

| Param | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `date_from`, `date_to` | `string` | ❌ | Khoảng thời gian |
| `time_range` | `string` | ❌ | `enum("day", "week", "month")` |

**12.4a — BE trả về:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `total_questions` | `int` | Tổng câu hỏi |
| `questions_today` | `int` | Câu hỏi hôm nay |
| `avg_response_time` | `float` | Thời gian trả lời TB (giây) |
| `satisfaction_rate` | `float` | Tỷ lệ hài lòng (% 👍) |
| `daily_chart` | `array[{date: string, count: int}]` | Số câu hỏi theo ngày (line chart) |
| `by_lesson_chart` | `array[{lesson_title: string, count: int}]` | Câu hỏi theo bài giảng (bar chart) |

**12.4b — Object `TopAIQuestion`:**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `id` | `string (UUID)` | PK |
| `question` | `string` | Nội dung câu hỏi |
| `answer` | `string` | Câu trả lời AI |
| `sources` | `array[AISource]` | Nguồn trích dẫn |
| `lesson_title` | `string` | Bài giảng liên quan |
| `ask_count` | `int` | Số lần hỏi tương tự |
| `thumbs_up` | `int` | Số 👍 |
| `thumbs_down` | `int` | Số 👎 |
| `created_at` | `string (ISO 8601)` | Lần hỏi đầu tiên |

---

### 12.5 Cài đặt hệ thống (Admin)

> Màn hình: `A-21`

| # | Hành động | Endpoint |
|---|-----------|----------|
| 12.5a | Lấy danh sách cấu hình hệ thống | `GET /api/admin/settings` |
| 12.5b | Cập nhật cấu hình hệ thống | `PUT /api/admin/settings` |

> 📌 **Quy tắc nghiệp vụ & Kiến trúc Tab "Thông báo" trên Web Admin A-21 (khớp `09` §3.6, §5.5):**  
> 1. Toàn bộ tham số vận hành hệ thống được lưu trữ trong bảng `system_settings` dưới dạng key-value JSONB, chuẩn hóa đúng **17 khóa** đã chốt tại `09` §5.5.  
> 2. **Tab "Thông báo" trên A-21:** Giai đoạn 1 vận hành thông báo **thuần trong ứng dụng** (In-app notifications) được kích hoạt tự động theo các sự kiện hệ thống (ghi danh thành công, video pipeline hoàn tất/thất bại, xuất bản khóa học). Hệ thống không triển khai Push Notification (FCM), không lưu device token và không lưu cấu hình push/email trên bảng `system_settings`. Do đó, Tab "Thông báo" (cấu hình FCM, email server) trên Web Admin `A-21` thuộc diện **`[Dự phòng GĐ2]`** (trên UI hiển thị nhãn dự phòng hoặc ẩn trường cấu hình).

**12.5a — Lấy danh sách cấu hình hệ thống (`GET /api/admin/settings`):**

FE gửi lên: Header `Authorization` (Admin).

BE trả về (Response 200):

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `data` | `SystemSettingsData` | Object chứa toàn bộ 17 tham số cấu hình hệ thống |

**Object `SystemSettingsData` (chuẩn 17 keys từ `09` §5.5):**

| Khóa (Key) | Kiểu | Giá trị mặc định | Diễn giải nghiệp vụ |
|---|---|---|---|
| `embedding_active_version` | `string` | `"v1"` | Phiên bản model nhúng đang phục vụ |
| `embedding_dim` | `int` | `1536` | Số chiều véc-tơ (OpenAI text-embedding-3-small) |
| `retrieval_top_k` | `int` | `5` | Số chunk ứng viên trích xuất tối đa cho RAG |
| `retrieval_similarity_threshold` | `float` | `0.72` | Ngưỡng tương đồng cosine tối thiểu để trả lời |
| `retrieval_time_window_seconds` | `int` | `120` | Cửa sổ thời gian ưu tiên ngữ cảnh video (± giây) |
| `retrieval_time_weight` | `float` | `0.05` | Trọng số tăng trọng theo thời gian |
| `ai_qa_daily_limit` | `int` | `50` | Hạn mức câu hỏi AI / ngày / học viên |
| `ai_summary_daily_limit` | `int` | `10` | Hạn mức yêu cầu tóm tắt AI / ngày / học viên |
| `chunk_size_tokens` | `int` | `500` | Kích thước đoạn văn bản phân đoạn transcript |
| `chunk_overlap_tokens` | `int` | `90` | Độ chồng lấp giữa 2 chunk liên tiếp |
| `chunk_config_version` | `string` | `"c1"` | Phiên bản cấu hình chunking |
| `upload_max_part_bytes` | `int` | `209715200` | Kích thước tối đa mỗi part upload (200MB) |
| `upload_max_total_bytes` | `int` | `5368709120` | Kích thước tối đa tệp video nguyên vẹn (5GB) |
| `order_ttl_seconds` | `int` | `900` | Thời hạn thanh toán đơn hàng (15 phút) |
| `storage_public_base_url` | `string` | *(theo môi trường)* | Base URL dùng để phân phối tài nguyên qua Amazon CloudFront |
| `llm_primary_model` | `string` | `"gpt-4o-mini"` | Mô hình ngôn ngữ chính |
| `llm_fallback_model` | `string` | `"gemini-1.5-flash"` | Mô hình ngôn ngữ dự phòng khi lỗi |

---

**12.5b — Cập nhật cấu hình hệ thống (`PUT /api/admin/settings`):**

FE gửi lên: Header `Authorization` (Admin).

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|:---:|-------|
| `settings` | `object` | ✅ | Object chứa các cặp key-value cần cập nhật (chỉ gửi các key cần sửa) |

**BE trả về (Response 200):**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `updated_keys` | `array[string]` | Danh sách các khóa đã cập nhật thành công |
| `message` | `string` | `"Cập nhật cấu hình hệ thống thành công."` |

**Mã lỗi:**

| HTTP Code | Error Code | Ý nghĩa | FE hiển thị |
|-----------|------------|----------|-------------|
| `400` | `INVALID_SETTING_KEY` | Khóa không nằm trong danh mục 17 tham số hợp lệ | Inline: "Tham số cấu hình không hợp lệ" |
| `400` | `INVALID_SETTING_VALUE` | Kiểu dữ liệu hoặc giá trị tham số ngoài khoảng cho phép | Inline: "Giá trị cấu hình không hợp lệ" |
| `403` | `FORBIDDEN` | Không có quyền quản trị viên | Toast: "Bạn không có quyền thực hiện" |

---

## PHỤ LỤC A — BẢNG MÃ LỖI TOÀN CỤC

| HTTP Code | Error Code | Mô tả | Áp dụng |
|-----------|------------|-------|---------|
| `400` | `VALIDATION_ERROR` | Dữ liệu đầu vào không hợp lệ | Tất cả endpoint |
| `401` | `TOKEN_EXPIRED` | Access token hết hạn → cần refresh | Tất cả endpoint cần auth |
| `401` | `INVALID_TOKEN` | Token không hợp lệ | Tất cả endpoint cần auth |
| `401` | `REFRESH_TOKEN_INVALID` | Refresh token không hợp lệ | Refresh endpoint |
| `403` | `FORBIDDEN` | Không có quyền truy cập | Endpoint admin / enrolled-only |
| `403` | `NOT_ENROLLED` | Chưa mua/đăng ký khóa học | Lesson, AI, Quiz, Notes |
| `403` | `ACCOUNT_LOCKED` | Tài khoản bị khóa | Login |
| `404` | `NOT_FOUND` | Tài nguyên không tồn tại | Tất cả GET by ID |
| `409` | `CONFLICT` | Xung đột dữ liệu (trùng, đã tồn tại) | Register, Enroll, Delete |
| `413` | `PAYLOAD_TOO_LARGE` | File upload quá lớn | Upload endpoints |
| `429` | `RATE_LIMITED` | Quá nhiều request | Login, AI Q&A, OTP |
| `500` | `INTERNAL_ERROR` | Lỗi hệ thống | Tất cả |
| `502` | `BAD_GATEWAY` | Service phụ thuộc không phản hồi | PayOS, AI service |
| `503` | `SERVICE_UNAVAILABLE` | Service tạm ngừng | Pipeline, AI |
| `504` | `GATEWAY_TIMEOUT` | Timeout từ service phụ thuộc | AI Q&A, AI Summary |

---

## PHỤ LỤC B — RESPONSE ERROR FORMAT CHUẨN

Tất cả response lỗi tuân theo format thống nhất:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Mô tả lỗi dạng human-readable",
    "details": {
      "field_name": ["Chi tiết lỗi cho field cụ thể"]
    }
  }
}
```

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `error.code` | `string` | Mã lỗi (UPPER_SNAKE_CASE) — FE dùng để phân biệt logic |
| `error.message` | `string` | Mô tả chung (có thể hiển thị cho user) |
| `error.details` | `object?` | Chi tiết lỗi per field (nullable, dùng cho 400/422) |

---

## PHỤ LỤC C — RESPONSE WRAPPER CHUẨN

**Thành công (single object):**

```json
{
  "data": { ... },
  "message": "OK"
}
```

**Thành công (danh sách có phân trang):**

```json
{
  "data": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

---

## PHỤ LỤC D — TỔNG HỢP ENDPOINT

| # | Nhóm | Method | Endpoint | Auth | Platform |
|---|------|--------|----------|:---:|----------|
| 1.1 | Auth | `POST` | `/api/auth/register` | ❌ | Mobile |
| 1.2 | Auth | `POST` | `/api/auth/verify-otp` | ❌ | Mobile |
| 1.3 | Auth | `POST` | `/api/auth/resend-otp` | ❌ | Mobile |
| 1.4 | Auth | `POST` | `/api/auth/login` | ❌ | Both |
| 1.5 | Auth | `POST` | `/api/auth/refresh` | ❌ | Both |
| 1.6 | Auth | `POST` | `/api/auth/logout` | ✅ | Both |
| 1.7 | Auth | `POST` | `/api/auth/forgot-password` | ❌ | Mobile |
| 1.8 | Auth | `POST` | `/api/auth/reset-password` | ❌ | Mobile |
| 2.1 | Course | `GET` | `/api/courses/featured` | ❌ | Mobile |
| 2.2 | Course | `GET` | `/api/progress/continue` | ✅ | Mobile |
| 2.3 | Course | `GET` | `/api/courses` | ❌ | Both |
| 2.4 | Course | `GET` | `/api/categories` | ❌ | Both |
| 2.5 | Course | `GET` | `/api/courses/{course_id}` | ❌* | Both |
| 2.6 | Course | `POST` | `/api/courses/{course_id}/enroll` | ✅ | Mobile |
| 2.7 | Lesson | `GET` | `/api/lessons/{lesson_id}` | ✅ | Mobile |
| 2.8 | Course | `GET` | `/api/my-courses` | ✅ | Mobile |
| 2.9 | Admin | `POST` | `/api/admin/courses` | ✅ | Web |
| 2.10 | Admin | `PUT` | `/api/admin/courses/{course_id}` | ✅ | Web |
| 2.11 | Admin | `DELETE` | `/api/admin/courses/{course_id}` | ✅ | Web |
| 2.12a | Admin | `POST` | `/api/admin/courses/{course_id}/chapters` | ✅ | Web |
| 2.12b | Admin | `PUT` | `/api/admin/chapters/{chapter_id}` | ✅ | Web |
| 2.12c | Admin | `DELETE` | `/api/admin/chapters/{chapter_id}` | ✅ | Web |
| 2.12d | Admin | `PUT` | `/api/admin/courses/{course_id}/reorder` | ✅ | Web |
| 2.13a | Admin | `POST` | `/api/admin/chapters/{chapter_id}/lessons` | ✅ | Web |
| 2.13b | Admin | `PUT` | `/api/admin/lessons/{lesson_id}` | ✅ | Web |
| 2.13c | Admin | `DELETE` | `/api/admin/lessons/{lesson_id}` | ✅ | Web |
| 3.1 | Progress | `POST` | `/api/progress` | ✅ | Mobile |
| 3.2 | Progress | `GET` | `/api/progress/overview` | ✅ | Mobile |
| 4.1 | AI | `POST` | `/api/lessons/{lesson_id}/ask` | ✅ | Mobile |
| 4.2 | AI | `GET` | `/api/lessons/{lesson_id}/chat-history` | ✅ | Mobile |
| 4.3 | AI | `GET` | `/api/lessons/{lesson_id}/suggested-questions` | ✅ | Mobile |
| 4.4 | AI | `POST` | `/api/ai-messages/{message_id}/feedback` | ✅ | Mobile |
| 5.1 | AI | `POST` | `/api/lessons/{lesson_id}/summarize` | ✅ | Mobile |
| 6.1 | Quiz | `GET` | `/api/quizzes/{quiz_id}` | ✅ | Mobile |
| 6.2 | Quiz | `POST` | `/api/quiz-responses` | ✅ | Mobile |
| 6.3 | Exercise | `GET` | `/api/exercises/{exercise_id}` | ✅ | Mobile |
| 6.4 | Exercise | `POST` | `/api/exercises/{exercise_id}/submit` | ✅ | Mobile |
| 6.5a | Admin | `GET` | `/api/admin/questions` | ✅ | Web |
| 6.5b | Admin | `POST` | `/api/admin/questions` | ✅ | Web |
| 6.5c | Admin | `PUT` | `/api/admin/questions/{question_id}` | ✅ | Web |
| 6.5d | Admin | `DELETE` | `/api/admin/questions/{question_id}` | ✅ | Web |
| 6.6a | Admin | `POST` | `/api/admin/exams` | ✅ | Web |
| 6.6b | Admin | `PUT` | `/api/admin/exams/{exam_id}` | ✅ | Web |
| 7.1 | Notes | `GET` | `/api/lessons/{lesson_id}/notes` | ✅ | Mobile |
| 7.2 | Notes | `POST` | `/api/lessons/{lesson_id}/notes` | ✅ | Mobile |
| 7.3 | Notes | `PUT` | `/api/notes/{note_id}` | ✅ | Mobile |
| 7.4 | Notes | `DELETE` | `/api/notes/{note_id}` | ✅ | Mobile |
| 8.1 | Payment | `POST` | `/api/orders` | ✅ | Mobile |
| 8.2 | Payment | `GET` | `/api/orders/{order_id}/status` | ✅ | Mobile |
| 8.3 | Payment | `PUT` | `/api/orders/{order_id}/cancel` | ✅ | Mobile |
| 8.4 | Payment | `POST` | `/api/webhooks/payos` | ❌ (HMAC) | Server-to-server |
| 9.1a | Pipeline | `POST` | `/api/admin/videos/upload/init` | ✅ | Web |
| 9.1b | Pipeline | `POST` | `/api/admin/videos/upload` | ✅ | Web |
| 9.1c | Pipeline | `POST` | `/api/admin/videos/upload/complete` | ✅ | Web |
| 9.2 | Pipeline | `GET` | `/api/admin/pipeline/{video_id}/status` | ✅ | Web |
| 9.3 | Pipeline | `GET` | `/api/admin/pipeline` | ✅ | Web |
| 9.4 | Pipeline | `POST` | `/api/admin/pipeline/{video_id}/retry` | ✅ | Web |
| 9.5 | Pipeline | `PUT` | `/api/admin/pipeline/{video_id}/cancel` | ✅ | Web |
| 9.6a | Transcript | `GET` | `/api/admin/lessons/{lesson_id}/transcript` | ✅ | Web |
| 9.6b | Transcript | `PUT` | `/api/admin/transcripts/{transcript_id}` | ✅ | Web |
| 10.1 | Notify | `GET` | `/api/notifications/unread-count` | ✅ | Mobile |
| 10.2 | Notify | `GET` | `/api/notifications` | ✅ | Mobile |
| 10.3 | Notify | `PUT` | `/api/notifications/{notification_id}/read` | ✅ | Mobile |
| 11.1 | User | `GET` | `/api/users/me` | ✅ | Both |
| 11.2 | User | `PUT` | `/api/users/me` | ✅ | Both |
| 11.3 | User | `PUT` | `/api/users/me/password` | ✅ | Both |
| 11.4a | Admin User | `GET` | `/api/admin/users` | ✅ | Web |
| 11.4b | Admin User | `PUT` | `/api/admin/users/{user_id}/lock` | ✅ | Web |
| 11.4c | Admin User | `PUT` | `/api/admin/users/{user_id}/unlock` | ✅ | Web |
| 12.1 | Report | `GET` | `/api/admin/dashboard` | ✅ | Web |
| 12.2a | Report | `GET` | `/api/admin/revenue/summary` | ✅ | Web |
| 12.2b | Report | `GET` | `/api/admin/revenue/chart` | ✅ | Web |
| 12.2c | Report | `GET` | `/api/admin/revenue/transactions` | ✅ | Web |
| 12.3 | Report | `GET` | `/api/admin/analytics/students` | ✅ | Web |
| 12.4a | Report | `GET` | `/api/admin/analytics/ai-questions` | ✅ | Web |
| 12.4b | Report | `GET` | `/api/admin/analytics/ai-questions/top` | ✅ | Web |
| 12.5a | Admin | `GET` | `/api/admin/settings` | ✅ | Web |
| 12.5b | Admin | `PUT` | `/api/admin/settings` | ✅ | Web |

> `❌*` = Không cần auth nhưng nếu có token thì trả thêm enrollment info.

---

## PHỤ LỤC E — MA TRẬN PHÂN QUYỀN THEO ENDPOINT

> Quy ước: **Auth** = có yêu cầu đăng nhập không · **Vai trò** = `student` hoặc `admin` · **Ghi danh** = có kiểm tra quyền ghi danh hoặc bài học thử không · **Sở hữu** = có kiểm tra tài nguyên thuộc về chính người gọi không.
> Đây là **nguồn duy nhất** cho tầng middleware/permission. Chỉ kiểm tra `Auth` mà bỏ qua `Ghi danh` hoặc `Sở hữu` là **lỗi bảo mật**. `[Derived]` — cần nhóm rà lại.

| # | Endpoint | Auth | Vai trò | Ghi danh | Sở hữu |
|---|---|:---:|---|:---:|:---:|
| 1.1 | `POST /api/auth/register` | ❌ | — | ❌ | ❌ |
| 1.2 | `POST /api/auth/verify-otp` | ❌ | — | ❌ | ❌ |
| 1.3 | `POST /api/auth/resend-otp` | ❌ | — | ❌ | ❌ |
| 1.4 | `POST /api/auth/login` | ❌ | — | ❌ | ❌ |
| 1.5 | `POST /api/auth/refresh` | ❌ | — | ❌ | ❌ |
| 1.6 | `POST /api/auth/logout` | ✅ | any | ❌ | ❌ |
| 1.7 | `POST /api/auth/forgot-password` | ❌ | — | ❌ | ❌ |
| 1.8 | `POST /api/auth/reset-password` | ❌ | — | ❌ | ❌ |
| 2.1 | `GET /api/courses/featured` | ❌ | — | ❌ | ❌ |
| 2.2 | `GET /api/progress/continue` | ✅ | student | ❌ | ✅ |
| 2.3 | `GET /api/courses` | ❌ | — | ❌ | ❌ |
| 2.4 | `GET /api/categories` | ❌ | — | ❌ | ❌ |
| 2.5 | `GET /api/courses/{course_id}` | ❌* | — | ❌ | ❌ |
| 2.6 | `POST /api/courses/{course_id}/enroll` | ✅ | student | ❌ | ✅ |
| 2.7 | `GET /api/lessons/{lesson_id}` | ✅ | student | ✅ (hoặc bài học thử) | ❌ |
| 2.8 | `GET /api/my-courses` | ✅ | student | ❌ | ✅ |
| 2.9 | `POST /api/admin/courses` | ✅ | admin | ❌ | ❌ |
| 2.10 | `PUT /api/admin/courses/{course_id}` | ✅ | admin | ❌ | ❌ |
| 2.11 | `DELETE /api/admin/courses/{course_id}` | ✅ | admin | ❌ | ❌ |
| 2.12a | `POST /api/admin/courses/{course_id}/chapters` | ✅ | admin | ❌ | ❌ |
| 2.12b | `PUT /api/admin/chapters/{chapter_id}` | ✅ | admin | ❌ | ❌ |
| 2.12c | `DELETE /api/admin/chapters/{chapter_id}` | ✅ | admin | ❌ | ❌ |
| 2.12d | `PUT /api/admin/courses/{course_id}/reorder` | ✅ | admin | ❌ | ❌ |
| 2.13a | `POST /api/admin/chapters/{chapter_id}/lessons` | ✅ | admin | ❌ | ❌ |
| 2.13b | `PUT /api/admin/lessons/{lesson_id}` | ✅ | admin | ❌ | ❌ |
| 2.13c | `DELETE /api/admin/lessons/{lesson_id}` | ✅ | admin | ❌ | ❌ |
| 3.1 | `POST /api/progress` | ✅ | student | ✅ | ✅ |
| 3.2 | `GET /api/progress/overview` | ✅ | student | ❌ | ✅ |
| 4.1 | `POST /api/lessons/{lesson_id}/ask` | ✅ | student | ✅ | ❌ |
| 4.2 | `GET /api/lessons/{lesson_id}/chat-history` | ✅ | student | ✅ | ✅ |
| 4.3 | `GET /api/lessons/{lesson_id}/suggested-questions` | ✅ | student | ✅ | ❌ |
| 4.4 | `POST /api/ai-messages/{message_id}/feedback` | ✅ | student | ❌ | ✅ |
| 5.1 | `POST /api/lessons/{lesson_id}/summarize` | ✅ | student | ✅ | ❌ |
| 6.1 | `GET /api/quizzes/{quiz_id}` | ✅ | student | ✅ | ❌ |
| 6.2 | `POST /api/quiz-responses` | ✅ | student | ✅ | ✅ |
| 6.3 | `GET /api/exercises/{exercise_id}` | ✅ | student | ✅ | ❌ |
| 6.4 | `POST /api/exercises/{exercise_id}/submit` | ✅ | student | ✅ | ✅ |
| 6.5a | `GET /api/admin/questions` | ✅ | admin | ❌ | ❌ |
| 6.5b | `POST /api/admin/questions` | ✅ | admin | ❌ | ❌ |
| 6.5c | `PUT /api/admin/questions/{question_id}` | ✅ | admin | ❌ | ❌ |
| 6.5d | `DELETE /api/admin/questions/{question_id}` | ✅ | admin | ❌ | ❌ |
| 6.6a | `POST /api/admin/exams` | ✅ | admin | ❌ | ❌ |
| 6.6b | `PUT /api/admin/exams/{exam_id}` | ✅ | admin | ❌ | ❌ |

> `❌*` = không bắt buộc token, nhưng nếu có token hợp lệ thì trả thêm thông tin ghi danh và tiến độ của học viên.
> Riêng `GET /api/courses` (2.3): khi người gọi là `admin` thì trả cả khóa học `draft` và `hidden`; học viên chỉ thấy `published`.

| 7.1 | `GET /api/lessons/{lesson_id}/notes` | ✅ | student | ✅ | ✅ |
| 7.2 | `POST /api/lessons/{lesson_id}/notes` | ✅ | student | ✅ | ✅ |
| 7.3 | `PUT /api/notes/{note_id}` | ✅ | student | ❌ | ✅ |
| 7.4 | `DELETE /api/notes/{note_id}` | ✅ | student | ❌ | ✅ |
| 8.1 | `POST /api/orders` | ✅ | student | ❌ | ✅ |
| 8.2 | `GET /api/orders/{order_id}/status` | ✅ | student | ❌ | ✅ |
| 8.3 | `PUT /api/orders/{order_id}/cancel` | ✅ | student | ❌ | ✅ |
| 8.4 | `POST /api/webhooks/payos` | ❌ | HMAC (server-to-server) | ❌ | ❌ |
| 9.1a | `POST /api/admin/videos/upload/init` | ✅ | admin | ❌ | ❌ |
| 9.1b | `POST /api/admin/videos/upload` | ✅ | admin | ❌ | ❌ |
| 9.1c | `POST /api/admin/videos/upload/complete` | ✅ | admin | ❌ | ❌ |
| 9.2 | `GET /api/admin/pipeline/{video_id}/status` | ✅ | admin | ❌ | ❌ |
| 9.3 | `GET /api/admin/pipeline` | ✅ | admin | ❌ | ❌ |
| 9.4 | `POST /api/admin/pipeline/{video_id}/retry` | ✅ | admin | ❌ | ❌ |
| 9.5 | `PUT /api/admin/pipeline/{video_id}/cancel` | ✅ | admin | ❌ | ❌ |
| 9.6a | `GET /api/admin/lessons/{lesson_id}/transcript` | ✅ | admin | ❌ | ❌ |
| 9.6b | `PUT /api/admin/transcripts/{transcript_id}` | ✅ | admin | ❌ | ❌ |
| 10.1 | `GET /api/notifications/unread-count` | ✅ | any | ❌ | ✅ |
| 10.2 | `GET /api/notifications` | ✅ | any | ❌ | ✅ |
| 10.3 | `PUT /api/notifications/{notification_id}/read` | ✅ | any | ❌ | ✅ |
| 11.1 | `GET /api/users/me` | ✅ | any | ❌ | ✅ |
| 11.2 | `PUT /api/users/me` | ✅ | any | ❌ | ✅ |
| 11.3 | `PUT /api/users/me/password` | ✅ | any | ❌ | ✅ |
| 11.4a | `GET /api/admin/users` | ✅ | admin | ❌ | ❌ |
| 11.4b | `PUT /api/admin/users/{user_id}/lock` | ✅ | admin | ❌ | ❌ |
| 11.4c | `PUT /api/admin/users/{user_id}/unlock` | ✅ | admin | ❌ | ❌ |
| 12.1 | `GET /api/admin/dashboard` | ✅ | admin | ❌ | ❌ |
| 12.2a | `GET /api/admin/revenue/summary` | ✅ | admin | ❌ | ❌ |
| 12.2b | `GET /api/admin/revenue/chart` | ✅ | admin | ❌ | ❌ |
| 12.2c | `GET /api/admin/revenue/transactions` | ✅ | admin | ❌ | ❌ |
| 12.3 | `GET /api/admin/analytics/students` | ✅ | admin | ❌ | ❌ |
| 12.4a | `GET /api/admin/analytics/ai-questions` | ✅ | admin | ❌ | ❌ |
| 12.4b | `GET /api/admin/analytics/ai-questions/top` | ✅ | admin | ❌ | ❌ |
| 12.5a | `GET /api/admin/settings` | ✅ | admin | ❌ | ❌ |
| 12.5b | `PUT /api/admin/settings` | ✅ | admin | ❌ | ❌ |

> Với 10.1–10.3: học viên chỉ thấy thông báo của chính mình cộng với thông báo quảng bá (`user_id IS NULL`); không được đọc hoặc đánh dấu đã đọc thông báo của người khác.
> Ba quy tắc xoá mềm bắt buộc: (1) mọi truy vấn đọc public luôn lọc `deleted_at IS NULL`; (2) xoá mềm khóa học thì ẩn khỏi danh sách nhưng **giữ nguyên** ghi danh và tiến độ cho học viên đã mua; (3) chỉ mục duy nhất `LOWER(email)` là **toàn cục** nên tài khoản đã xoá mềm vẫn giữ email — phải mở lại tài khoản thay vì đăng ký mới.

## PHỤ LỤC F — VÍ DỤ JSON MẪU

> Các ví dụ dưới đây chỉ dùng trường đã định nghĩa trong tài liệu này; dùng làm mẫu ràng buộc shape cho Pydantic schema và cho kiểm thử tích hợp.

**F.1 — 4.1 Hỏi AI (trong phạm vi bài giảng, HTTP 200):**

```json
{
  "data": {
    "id": "3f1c8b2e-9a54-4f7d-8c31-2b6e5a0d7f19",
    "answer": "Khái niệm **đệ quy** là kỹ thuật một hàm gọi lại chính nó...",
    "sources": [
      {
        "chunk_id": "b7d2f0a1-4c63-4e0a-9f2b-6d81c4a93e57",
        "text": "Đệ quy là kỹ thuật trong đó một hàm gọi lại chính nó để giải bài toán nhỏ hơn...",
        "start_time": 412.5,
        "end_time": 445.0,
        "relevance_score": 0.86
      }
    ],
    "processing_time": 2.41,
    "questions_remaining": 47,
    "daily_limit": 50,
    "is_out_of_scope": false
  },
  "message": "OK"
}
```

**F.2 — 4.1 Hỏi AI ngoài phạm vi bài giảng (vẫn HTTP 200):**

```json
{
  "data": {
    "id": "9a02e1f4-77bd-4c9a-8e15-0c3d6b71aa42",
    "answer": "Nội dung này không nằm trong phạm vi bài giảng hiện tại nên mình chưa thể trả lời. Bạn hãy hỏi về nội dung bài học đang xem nhé.",
    "sources": [],
    "processing_time": 0.12,
    "questions_remaining": 46,
    "daily_limit": 50,
    "is_out_of_scope": true
  },
  "message": "OK"
}
```

**F.3 — 6.4 Nộp bài tập (đã chấm tự động):**

```json
{
  "data": {
    "attempt_id": "c41d5e77-2b19-4a83-9d0f-5e17b2c8a340",
    "status": "graded",
    "score": 8,
    "attempts_remaining": 1,
    "details": [
      {
        "question_id": "e5b3a920-6c14-4f2d-8b71-1d94a7c30e58",
        "correct": true,
        "correct_answer": "A",
        "explanation": "Đáp án A đúng vì độ phức tạp trung bình là O(n log n)."
      }
    ]
  },
  "message": "OK"
}
```

**F.4 — 12.4a Thống kê câu hỏi AI (Admin):**

```json
{
  "data": {
    "total_questions": 1840,
    "questions_today": 73,
    "avg_response_time": 2.6,
    "satisfaction_rate": 91.4,
    "daily_chart": [{ "date": "2026-09-24", "count": 65 }],
    "by_lesson_chart": [{ "lesson_title": "Bài 3: Đệ quy", "count": 212 }]
  },
  "message": "OK"
}
```

**F.5 — 12.4b Câu hỏi AI phổ biến (danh sách phân trang):**

```json
{
  "data": [
    {
      "id": "3f1c8b2e-9a54-4f7d-8c31-2b6e5a0d7f19",
      "question": "Đệ quy khác vòng lặp ở điểm nào?",
      "answer": "Đệ quy gọi lại chính hàm đang xử lý...",
      "sources": [],
      "lesson_title": "Bài 3: Đệ quy",
      "ask_count": 37,
      "thumbs_up": 21,
      "thumbs_down": 2,
      "created_at": "2026-09-12T03:20:11Z"
    }
  ],
  "total": 37,
  "page": 1,
  "page_size": 20,
  "total_pages": 2
}
```

**F.6 — 6.3 Lấy bài tập cuối bài (dạng học viên làm bài, không lộ đáp án):**

```json
{
  "data": {
    "id": "7d8e9f01-3a2b-4c5d-8e6f-9012345678ab",
    "title": "Bài tập cuối bài 3",
    "time_limit": 900,
    "passing_score": 70,
    "max_attempts": 3,
    "attempts_used": 1,
    "questions": [
      {
        "question_id": "e5b3a920-6c14-4f2d-8b71-1d94a7c30e58",
        "content": "Độ phức tạp trung bình của QuickSort là gì?",
        "question_type": "single_choice",
        "options": [
          { "id": "12ab34cd-5678-4901-8234-5678901234ab", "label": "A", "content": "O(n log n)" }
        ]
      }
    ]
  },
  "message": "OK"
}
```

**F.7 — 2.3 Danh sách khóa học (phân trang):**

```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f56789",
      "title": "Lập trình Python cơ bản",
      "price": 0,
      "status": "published"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**F.8 — Lỗi kiểm tra dữ liệu đầu vào (HTTP 400):**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dữ liệu gửi lên không hợp lệ.",
    "details": {
      "email": ["Email không đúng định dạng"],
      "password": ["Mật khẩu phải có ít nhất 8 ký tự"]
    }
  }
}
```

## TỔNG HỢP THỐNG KÊ

| Hạng mục | Số lượng |
|----------|----------|
> Số liệu dưới đây được đối chiếu khớp với bảng ở **PHỤ LỤC D** (tổng cộng 78 dòng endpoint).

| Hạng mục | Số lượng |
|----------|----------|
| Tổng số endpoint | **78** |
| Nhóm Authentication | **8** endpoint |
| Nhóm Khóa học & Bài giảng | **18** endpoint |
| Nhóm Tiến độ học tập | **2** endpoint |
| Nhóm AI Q&A + Tóm tắt | **5** endpoint |
| Nhóm Quiz & Bài tập | **10** endpoint |
| Nhóm Ghi chú | **4** endpoint |
| Nhóm Thanh toán | **4** endpoint |
| Nhóm Pipeline video & Transcript | **9** endpoint |
| Nhóm Thông báo | **3** endpoint |
| Nhóm Hồ sơ cá nhân & quản lý học viên | **6** endpoint |
| Nhóm Báo cáo, Thống kê & Cài đặt hệ thống (Admin) | **9** endpoint |
| Tổng mã lỗi cần phân biệt | **~19** error code riêng biệt |
| Tổng data object được định nghĩa | **~36** object schema |

---

> **Ghi chú:** Tài liệu này là **góc nhìn từ Frontend** về dữ liệu cần trao đổi. Backend team sử dụng làm cơ sở thiết kế API chính xác. Mọi thay đổi field name, kiểu dữ liệu hoặc thêm/bớt endpoint cần cập nhật lại tài liệu và thông báo cho FE team.
