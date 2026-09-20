# Use Case Specification

> **Dự án:** Xây dựng nền tảng học trực tuyến thông minh tích hợp AI Trợ giảng tương tác ngữ cảnh bài giảng  
> **Phiên bản:** 1.0 — Ngày tạo: 08/09/2026  
> **Nguồn tham chiếu:** `01_Feature_Screen_Inventory.md`, Đề cương chi tiết (De_Cuong_DA1)

---

## 1. Danh sách Actor

| Actor | Mô tả | Sản phẩm tương tác | Ghi chú |
|-------|--------|---------------------|---------|
| **Học viên** (Student) | Người dùng cuối sử dụng ứng dụng di động để học trực tuyến, tương tác với AI Trợ giảng, làm bài tập, thanh toán khóa học. | Mobile App (Android Native — Kotlin, Media3/ExoPlayer) | Actor chính |
| **Quản trị viên** (Admin) | Người quản trị toàn bộ hệ thống: quản lý nội dung khóa học, xử lý video pipeline, quản lý đề thi, doanh thu, phân tích dữ liệu. Đảm nhiệm luôn vai trò Giảng viên ở giai đoạn này. | Web Admin (Next.js + Tailwind CSS) | Không có role Giảng viên riêng |

---

## 2. Danh sách Use Case theo Actor

### 2.1. Học viên — Mobile App

| Mã UC | Tên Use Case | Mã chức năng | Độ ưu tiên | Đặc tả chi tiết |
|-------|-------------|--------------|-------------|------------------|
| UC-01 | Đăng ký tài khoản | MOB-01 | Cao | ✅ Có |
| UC-02 | Đăng nhập | MOB-02 | Cao | ✅ Có |
| UC-03 | Quên mật khẩu / Đặt lại mật khẩu | MOB-03 | Cao | ✅ Có |
| UC-04 | Quản lý hồ sơ cá nhân | MOB-04 | Trung bình | — |
| UC-05 | Duyệt danh sách khóa học | MOB-05 | Cao | ✅ Có |
| UC-06 | Xem chi tiết khóa học | MOB-06 | Cao | ✅ Có |
| UC-07 | Thanh toán khóa học (PayOS/VietQR) | MOB-07 | Cao | ✅ Có |
| UC-08 | Xem video bài giảng trực tuyến (HLS) | MOB-08 | Cao | ✅ Có |
| UC-09 | Phụ đề đồng bộ theo thời gian thực | MOB-09 | Cao | ✅ Có |
| UC-10 | Đặt câu hỏi cho AI Trợ giảng (RAG Q&A) | MOB-10 | Cao | ✅ Có |
| UC-11 | Tóm tắt bài giảng bằng AI | MOB-11 | Cao | ✅ Có |
| UC-12 | Chia chương bài học | MOB-12 | Cao | ✅ Có |
| UC-13 | Ghi chú theo mốc thời gian video | MOB-13 | Cao | ✅ Có |
| UC-14 | Làm bài kiểm tra giữa video (Quiz) | MOB-14 | Cao | ✅ Có |
| UC-15 | Làm bài tập trắc nghiệm / tự luận | MOB-15 | Cao | ✅ Có |
| UC-16 | Theo dõi tiến độ học tập | MOB-16 | Cao | ✅ Có |
| UC-17 | Xem khóa học đã mua / Thư viện cá nhân | MOB-17 | Cao | ✅ Có |
| UC-18 | Xem lịch sử thanh toán | MOB-18 | Trung bình | — |
| UC-19 | Cache offline / Xử lý mất mạng | MOB-19 | Trung bình | — |
| UC-20 | Đăng xuất | MOB-20 | Cao | ✅ Có |
| UC-21 | Onboarding / Giới thiệu ứng dụng | MOB-21 | Thấp | — |
| UC-22 | Thông báo (Notifications) | MOB-22 | Trung bình | — |

### 2.2. Quản trị viên — Web Admin

| Mã UC | Tên Use Case | Mã chức năng | Độ ưu tiên | Đặc tả chi tiết |
|-------|-------------|--------------|-------------|------------------|
| UC-23 | Đăng nhập Admin | ADM-01 | Cao | ✅ Có |
| UC-24 | Xem Dashboard tổng quan | ADM-02 | Cao | ✅ Có |
| UC-25 | Quản lý khóa học (CRUD) | ADM-03 | Cao | ✅ Có |
| UC-26 | Quản lý cấu trúc bài giảng | ADM-04 | Cao | ✅ Có |
| UC-27 | Upload video bài giảng | ADM-05 | Cao | ✅ Có |
| UC-28 | Xử lý video tự động — Pipeline (STT → Vector Indexing) | ADM-06 | Cao | ✅ Có |
| UC-29 | Duyệt / Chỉnh sửa phụ đề (Transcript) | ADM-07 | Cao | ✅ Có |
| UC-30 | Quản lý ngân hàng đề thi | ADM-08 | Cao | ✅ Có |
| UC-31 | Quản lý bài tập | ADM-09 | Cao | ✅ Có |
| UC-32 | Quản lý học viên | ADM-10 | Trung bình | — |
| UC-33 | Quản lý doanh thu | ADM-11 | Cao | ✅ Có |
| UC-34 | Xem báo cáo phân tích hành vi học viên | ADM-12 | Cao | ✅ Có |
| UC-35 | Xem thống kê câu hỏi AI | ADM-13 | Cao | ✅ Có |
| UC-36 | Quản lý danh mục khóa học | ADM-14 | Trung bình | — |
| UC-37 | Cài đặt hệ thống | ADM-15 | Trung bình | — |
| UC-38 | Đăng xuất Admin | ADM-16 | Cao | ✅ Có |

---

## 3. Đặc tả chi tiết Use Case (Ưu tiên Cao)

---

### UC-01: Đăng ký tài khoản

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-01 |
| **Tên** | Đăng ký tài khoản |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên tạo tài khoản mới trên ứng dụng di động bằng email và mật khẩu. Hệ thống xác thực đầu vào, gửi mã OTP hoặc link xác nhận email, và kích hoạt tài khoản sau khi xác thực thành công. |
| **Màn hình liên quan** | M-04 (Đăng ký) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã cài đặt ứng dụng trên thiết bị Android.
- Thiết bị có kết nối internet.
- Học viên chưa có tài khoản trong hệ thống (hoặc chưa đăng nhập).

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Tại màn hình Đăng nhập (M-03), nhấn link "Đăng ký tài khoản mới". |
| 2 | Hệ thống | Hiển thị màn hình Đăng ký (M-04) với form: Họ tên, Email, Mật khẩu, Xác nhận mật khẩu. |
| 3 | Học viên | Nhập đầy đủ thông tin và nhấn nút "Đăng ký". |
| 4 | Hệ thống | Validate đầu vào: kiểm tra định dạng email, độ dài mật khẩu (≥ 8 ký tự, có chữ hoa, số, ký tự đặc biệt), mật khẩu xác nhận khớp, họ tên không trống. |
| 5 | Hệ thống | Kiểm tra email chưa được đăng ký trong cơ sở dữ liệu. |
| 6 | Hệ thống | Tạo tài khoản với trạng thái "Chưa xác thực". Gửi mã OTP (6 chữ số) đến email đã nhập. |
| 7 | Hệ thống | Chuyển sang màn hình nhập mã OTP. Hiển thị thông báo "Mã xác nhận đã được gửi đến email [email]". |
| 8 | Học viên | Mở email, lấy mã OTP, nhập vào ứng dụng và nhấn "Xác nhận". |
| 9 | Hệ thống | Xác thực mã OTP (kiểm tra đúng mã, chưa hết hạn — 5 phút). |
| 10 | Hệ thống | Cập nhật trạng thái tài khoản thành "Đã xác thực". Tự động đăng nhập, tạo JWT token + refresh token, chuyển đến Trang chủ (M-06). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 1a | Validate đầu vào thất bại (bước 4) | Hiển thị inline error tại từng trường lỗi (VD: "Email không hợp lệ", "Mật khẩu phải có ít nhất 8 ký tự"). Học viên sửa lại và submit. |
| 1b | Email đã tồn tại trong hệ thống (bước 5) | Hiển thị thông báo "Email này đã được đăng ký. Vui lòng đăng nhập hoặc sử dụng email khác." Cung cấp link chuyển sang màn hình Đăng nhập. |
| 1c | Mã OTP sai (bước 9) | Hiển thị thông báo "Mã xác nhận không đúng. Vui lòng kiểm tra lại." Cho phép nhập lại (tối đa 5 lần). |
| 1d | Mã OTP hết hạn (bước 9) | Hiển thị thông báo "Mã xác nhận đã hết hạn." Hiển thị nút "Gửi lại mã" — gửi OTP mới với thời hạn 5 phút. |
| 1e | Vượt quá số lần nhập OTP sai (5 lần) | Khóa chức năng xác thực trong 15 phút. Hiển thị thông báo "Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút." |
| 1f | Lỗi mạng / server | Hiển thị thông báo lỗi chung, cho phép thử lại. |

**Điều kiện kết thúc (Post-condition):**
- Tài khoản học viên mới được tạo trong cơ sở dữ liệu với trạng thái "Đã xác thực".
- Học viên được đăng nhập tự động và chuyển đến Trang chủ.
- JWT token và refresh token được lưu trên thiết bị.

---

### UC-02: Đăng nhập

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-02 |
| **Tên** | Đăng nhập |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên đăng nhập vào ứng dụng bằng email và mật khẩu đã đăng ký. Hệ thống xác thực thông tin, cấp JWT token, và chuyển đến Trang chủ. |
| **Màn hình liên quan** | M-03 (Đăng nhập) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã có tài khoản đã xác thực trong hệ thống.
- Học viên chưa đăng nhập (chưa có phiên hoạt động hợp lệ).
- Thiết bị có kết nối internet.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Hệ thống | Hiển thị Splash Screen (M-01), kiểm tra JWT token lưu trên thiết bị. |
| 2 | Hệ thống | Không tìm thấy token hợp lệ → Hiển thị màn hình Đăng nhập (M-03) với form: Email, Mật khẩu, nút "Đăng nhập", link "Đăng ký", link "Quên mật khẩu". |
| 3 | Học viên | Nhập email và mật khẩu, nhấn nút "Đăng nhập". |
| 4 | Hệ thống | Validate đầu vào: email không trống và đúng định dạng, mật khẩu không trống. |
| 5 | Hệ thống | Gửi request xác thực đến Backend (POST /api/auth/login). Backend kiểm tra email tồn tại, mật khẩu đúng (bcrypt hash compare). |
| 6 | Hệ thống | Xác thực thành công → Backend trả về JWT access token (thời hạn 15 phút) và refresh token (thời hạn 30 ngày). |
| 7 | Hệ thống | Lưu token trên thiết bị (EncryptedSharedPreferences). Chuyển đến Trang chủ (M-06). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 2a | Token hợp lệ được tìm thấy trên thiết bị (bước 1) | Hệ thống gọi API refresh token → Nếu thành công: chuyển thẳng đến Trang chủ (M-06), bỏ qua màn hình đăng nhập. Nếu thất bại (token hết hạn): hiển thị màn hình Đăng nhập. |
| 2b | Email hoặc mật khẩu sai (bước 5) | Hiển thị thông báo "Email hoặc mật khẩu không đúng." Không chỉ rõ trường nào sai (bảo mật). |
| 2c | Tài khoản chưa xác thực email (bước 5) | Hiển thị thông báo "Tài khoản chưa được xác thực. Vui lòng kiểm tra email." Hiển thị nút "Gửi lại mã xác nhận". |
| 2d | Tài khoản bị khóa bởi Admin (bước 5) | Hiển thị thông báo "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên." |
| 2e | Đăng nhập sai quá 5 lần liên tiếp | Khóa đăng nhập trong 15 phút. Hiển thị thông báo kèm thời gian chờ. |
| 2f | Lỗi mạng / server | Hiển thị thông báo lỗi kết nối, nút "Thử lại". |

**Điều kiện kết thúc (Post-condition):**
- Học viên được xác thực thành công.
- JWT access token và refresh token được lưu an toàn trên thiết bị.
- Học viên được chuyển đến Trang chủ và có thể sử dụng toàn bộ chức năng ứng dụng.

---

### UC-03: Quên mật khẩu / Đặt lại mật khẩu

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-03 |
| **Tên** | Quên mật khẩu / Đặt lại mật khẩu |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên yêu cầu đặt lại mật khẩu khi quên. Hệ thống gửi mã OTP qua email, xác thực mã, và cho phép tạo mật khẩu mới. |
| **Màn hình liên quan** | M-05 (Quên mật khẩu — multi-step) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã có tài khoản đăng ký trong hệ thống.
- Thiết bị có kết nối internet.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Tại màn hình Đăng nhập (M-03), nhấn link "Quên mật khẩu?". |
| 2 | Hệ thống | Hiển thị Bước 1 — Form nhập email. |
| 3 | Học viên | Nhập email đã đăng ký và nhấn "Tiếp tục". |
| 4 | Hệ thống | Kiểm tra email tồn tại trong hệ thống. Gửi mã OTP (6 chữ số, hạn 5 phút) đến email. |
| 5 | Hệ thống | Hiển thị Bước 2 — Form nhập mã OTP, kèm thông báo "Mã xác nhận đã gửi đến [email]". |
| 6 | Học viên | Nhập mã OTP nhận được qua email, nhấn "Xác nhận". |
| 7 | Hệ thống | Xác thực mã OTP hợp lệ. Hiển thị Bước 3 — Form nhập mật khẩu mới + xác nhận mật khẩu mới. |
| 8 | Học viên | Nhập mật khẩu mới, xác nhận, nhấn "Đặt lại mật khẩu". |
| 9 | Hệ thống | Validate mật khẩu mới (≥ 8 ký tự, đủ phức tạp). Cập nhật mật khẩu trong cơ sở dữ liệu (bcrypt hash). |
| 10 | Hệ thống | Hiển thị thông báo "Mật khẩu đã được đặt lại thành công." Chuyển về màn hình Đăng nhập (M-03). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 3a | Email không tồn tại trong hệ thống (bước 4) | Hiển thị thông báo chung "Nếu email này tồn tại trong hệ thống, mã xác nhận sẽ được gửi." (tránh lộ thông tin email nào đã đăng ký). |
| 3b | Mã OTP sai (bước 7) | Hiển thị thông báo "Mã xác nhận không đúng." Cho phép nhập lại (tối đa 5 lần). |
| 3c | Mã OTP hết hạn (bước 7) | Hiển thị nút "Gửi lại mã" — quay về bước 4 gửi OTP mới. |
| 3d | Mật khẩu mới không đạt yêu cầu (bước 9) | Hiển thị inline error mô tả cụ thể yêu cầu mật khẩu. |

**Điều kiện kết thúc (Post-condition):**
- Mật khẩu của học viên được cập nhật thành công trong cơ sở dữ liệu.
- Tất cả phiên đăng nhập cũ (refresh token cũ) bị thu hồi.
- Học viên cần đăng nhập lại bằng mật khẩu mới.

---

### UC-05: Duyệt danh sách khóa học

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-05 |
| **Tên** | Duyệt danh sách khóa học |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên xem danh sách khóa học có sẵn trên hệ thống, sử dụng bộ lọc (danh mục, giá, đánh giá) và tìm kiếm theo từ khóa để tìm khóa học phù hợp. |
| **Màn hình liên quan** | M-06 (Trang chủ), M-07 (Khám phá / Duyệt khóa học), M-08 (Kết quả tìm kiếm) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã đăng nhập vào ứng dụng.
- Có ít nhất 1 khóa học đã xuất bản (trạng thái "published") trong hệ thống.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Truy cập Trang chủ (M-06) hoặc nhấn tab "Khám phá" để mở màn hình Duyệt khóa học (M-07). |
| 2 | Hệ thống | Gọi API lấy danh sách khóa học (GET /api/courses). Hiển thị danh sách dạng card: ảnh bìa, tên, giảng viên, giá, đánh giá trung bình. Hỗ trợ phân trang (lazy loading / infinite scroll). |
| 3 | Học viên | (Tùy chọn) Sử dụng bộ lọc: chọn danh mục, khoảng giá, sắp xếp theo đánh giá/mới nhất/phổ biến. |
| 4 | Hệ thống | Gọi API với tham số bộ lọc, cập nhật danh sách khóa học hiển thị. |
| 5 | Học viên | (Tùy chọn) Nhập từ khóa vào thanh tìm kiếm, nhấn tìm kiếm. |
| 6 | Hệ thống | Gọi API tìm kiếm (GET /api/courses?q=keyword). Hiển thị kết quả trên M-08 (Kết quả tìm kiếm). |
| 7 | Học viên | Nhấn vào một khóa học để xem chi tiết → Chuyển đến UC-06 (Xem chi tiết khóa học). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 5a | Không có kết quả phù hợp | Hiển thị Empty State: illustration kèm thông báo "Không tìm thấy khóa học nào", gợi ý thay đổi bộ lọc hoặc từ khóa. |
| 5b | Đang tải dữ liệu | Hiển thị Loading State: skeleton cards cho danh sách khóa học. |
| 5c | Lỗi mạng | Hiển thị Error State: thông báo lỗi kết nối + nút "Thử lại". |

**Điều kiện kết thúc (Post-condition):**
- Học viên xem được danh sách khóa học phù hợp với tiêu chí lọc/tìm kiếm.
- Hoặc chuyển đến màn hình Chi tiết khóa học khi chọn một khóa.

---

### UC-06: Xem chi tiết khóa học

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-06 |
| **Tên** | Xem chi tiết khóa học |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên xem thông tin chi tiết của một khóa học: mô tả, danh sách chương/bài giảng, giá, đánh giá, thông tin giảng viên. Từ đây có thể mua khóa học hoặc tiếp tục học nếu đã mua. |
| **Màn hình liên quan** | M-09 (Chi tiết khóa học) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã đăng nhập.
- Khóa học tồn tại và đang ở trạng thái "Đã xuất bản".

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Nhấn vào một khóa học từ danh sách (M-06, M-07, hoặc M-08). |
| 2 | Hệ thống | Gọi API lấy chi tiết khóa học (GET /api/courses/{id}). Hiển thị M-09 với: tên khóa, mô tả chi tiết, ảnh bìa / video preview, danh sách chương và bài giảng (có thể expand/collapse), giá, đánh giá trung bình, số học viên đã đăng ký, thông tin giảng viên. |
| 3 | Hệ thống | Kiểm tra học viên đã mua khóa học này chưa. |
| 4a | Hệ thống | Nếu chưa mua → Hiển thị nút "Mua khóa học" với giá. |
| 4b | Hệ thống | Nếu đã mua → Hiển thị nút "Tiếp tục học" với tiến độ (%) và bài giảng tiếp theo. |
| 5 | Học viên | Nhấn "Mua khóa học" → Chuyển đến UC-07. HOẶC nhấn "Tiếp tục học" → Chuyển đến UC-08 (tại bài giảng dở dang). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 6a | Khóa học không tồn tại hoặc đã bị ẩn | Hiển thị thông báo "Khóa học không tồn tại hoặc đã bị gỡ." Nút quay lại danh sách. |
| 6b | Lỗi API | Hiển thị thông báo lỗi + nút "Thử lại". |

**Điều kiện kết thúc (Post-condition):**
- Học viên nắm được thông tin chi tiết khóa học.
- Học viên chuyển sang Thanh toán hoặc Xem video bài giảng.

---

### UC-07: Thanh toán khóa học (PayOS/VietQR)

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-07 |
| **Tên** | Thanh toán khóa học (PayOS/VietQR) |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên thực hiện thanh toán để mua khóa học thông qua mã QR VietQR tích hợp PayOS. Hệ thống tạo đơn hàng, hiển thị mã QR, tự động kiểm tra trạng thái giao dịch, và kích hoạt quyền truy cập khóa học khi thanh toán thành công. |
| **Màn hình liên quan** | M-10 (Thanh toán khóa học), M-11 (Kết quả thanh toán) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã đăng nhập.
- Học viên chưa mua khóa học này.
- Khóa học có giá > 0 (không phải khóa miễn phí).
- Cấu hình PayOS (API key, Merchant ID) đã được thiết lập bởi Admin.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Tại M-09 (Chi tiết khóa học), nhấn nút "Mua khóa học". |
| 2 | Hệ thống | Tạo đơn hàng (order) trong cơ sở dữ liệu với trạng thái "Chờ thanh toán". Gọi API PayOS tạo link thanh toán → nhận mã QR VietQR. |
| 3 | Hệ thống | Hiển thị M-10 (Thanh toán): thông tin đơn hàng (tên khóa học, giá), mã QR VietQR, hướng dẫn thanh toán ("Quét mã QR bằng ứng dụng ngân hàng"), countdown timer (15 phút). |
| 4 | Học viên | Mở ứng dụng ngân hàng, quét mã QR, và thực hiện chuyển khoản. |
| 5 | Hệ thống | Polling / Webhook từ PayOS kiểm tra trạng thái giao dịch (mỗi 3 giây). Hiển thị spinner "Đang chờ xác nhận thanh toán...". |
| 6 | Hệ thống (PayOS) | PayOS xác nhận giao dịch thành công → Gọi webhook đến Backend. |
| 7 | Hệ thống (Backend) | Cập nhật trạng thái đơn hàng thành "Đã thanh toán". Ghi nhận doanh thu. Cấp quyền truy cập khóa học cho học viên (enrollment). |
| 8 | Hệ thống | Hiển thị M-11 (Kết quả thanh toán thành công): thông báo "Thanh toán thành công!", nút "Bắt đầu học ngay" → chuyển đến bài giảng đầu tiên của khóa (UC-08). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 7a | Thanh toán thất bại (PayOS trả về lỗi) | Hiển thị M-11 (Kết quả thất bại): thông báo lý do (nếu có), nút "Thử lại" (tạo QR mới), nút "Quay lại". Cập nhật trạng thái đơn hàng thành "Thất bại". |
| 7b | Hết thời gian chờ (timeout 15 phút) | Hiển thị thông báo "Đã hết thời gian thanh toán." Hủy đơn hàng hiện tại. Nút "Tạo mã thanh toán mới". |
| 7c | Khóa học miễn phí (giá = 0) | Bỏ qua bước thanh toán. Hệ thống tự động đăng ký (enroll) học viên vào khóa, chuyển thẳng đến bài giảng đầu tiên. |
| 7d | Lỗi tạo mã QR (API PayOS lỗi) | Hiển thị thông báo "Không thể tạo mã thanh toán. Vui lòng thử lại sau." Nút "Thử lại". |
| 7e | Học viên nhấn "Hủy" trong khi chờ | Hỏi xác nhận hủy. Nếu xác nhận: hủy đơn hàng, quay lại M-09. |

**Điều kiện kết thúc (Post-condition):**
- Đơn hàng được ghi nhận trong cơ sở dữ liệu (thành công hoặc thất bại).
- Nếu thành công: Học viên được cấp quyền truy cập khóa học, giao dịch lưu trong lịch sử thanh toán, doanh thu được ghi nhận.
- Nếu thất bại/hủy: Không có thay đổi quyền truy cập.

---

### UC-08: Xem video bài giảng trực tuyến (HLS)

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-08 |
| **Tên** | Xem video bài giảng trực tuyến (HLS) |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên xem video bài giảng trực tuyến qua giao thức HLS (Cloudflare Stream/AWS CloudFront). Trình phát hỗ trợ play/pause, tua, chọn chất lượng, picture-in-picture, phụ đề đồng bộ, chia chương, và là điểm khởi đầu cho các tương tác AI (hỏi đáp, tóm tắt), ghi chú, quiz. |
| **Màn hình liên quan** | M-12 (Trình phát video bài giảng) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã đăng nhập.
- Học viên đã mua (enrolled) khóa học chứa bài giảng này.
- Video bài giảng đã được xử lý hoàn tất qua pipeline (trạng thái: sẵn sàng).
- Thiết bị có kết nối internet.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Chọn bài giảng từ danh sách chương/bài trong M-09 (Chi tiết khóa học), hoặc nhấn "Tiếp tục học" từ M-21 (Thư viện). |
| 2 | Hệ thống | Gọi API lấy thông tin bài giảng (GET /api/lessons/{id}). Lấy HLS stream URL (signed URL với thời hạn). Tải metadata: transcript, danh sách chương, mốc quiz. |
| 3 | Hệ thống | Khởi tạo ExoPlayer/Media3 với HLS source. Hiển thị M-12 (Trình phát video) với: video player toàn màn hình, thanh tiến trình (seekbar) với các markers (chương, quiz), nút play/pause, nút tua 10s trước/sau, nút chọn chất lượng video, nút bật/tắt phụ đề, nút picture-in-picture, danh sách chương (sidebar/drawer), nút mở Chat AI, nút ghi chú. |
| 4 | Hệ thống | Nếu học viên đã xem dở trước đó → Tự động tua đến vị trí dở dang (last_position từ API). |
| 5 | Học viên | Nhấn Play → Video bắt đầu phát. Phụ đề hiển thị đồng bộ (nếu bật). |
| 6 | Hệ thống | Định kỳ (mỗi 10 giây) gửi API cập nhật tiến độ xem (POST /api/progress). Lưu vị trí hiện tại, % đã xem. |
| 7 | Học viên | Sử dụng các control: tua, chuyển chương, thay đổi chất lượng, bật/tắt phụ đề, picture-in-picture. |
| 8 | Hệ thống | Khi đến mốc thời gian có quiz → Tự động pause video, hiển thị overlay quiz (UC-14). |
| 9 | Học viên | Khi xem xong video → Hệ thống đánh dấu bài giảng "Đã hoàn thành", cập nhật tiến độ khóa học. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 8a | Video không thể phát (lỗi HLS URL, video đang xử lý) | Hiển thị Error State: thông báo "Video chưa sẵn sàng hoặc đã xảy ra lỗi", nút "Thử lại", nút "Quay lại". |
| 8b | Mất kết nối mạng khi đang xem | Hiển thị overlay "Mất kết nối internet. Video sẽ tự động tiếp tục khi có mạng." Video tạm dừng, tự động resume khi kết nối lại. |
| 8c | Video buffer chậm | Hiển thị spinner buffering trên player. Nếu kéo dài > 15 giây: gợi ý giảm chất lượng video. |
| 8d | Học viên nhấn nút Chat AI | Mở bottom sheet Chat AI (UC-10) — video tiếp tục phát hoặc tạm dừng tùy thiết lập. |
| 8e | Học viên nhấn nút Ghi chú | Mở form ghi chú (UC-13) gắn với mốc thời gian hiện tại — video tạm dừng. |
| 8f | Học viên nhấn nút Tóm tắt AI | Mở bottom sheet tóm tắt (UC-11) — video tạm dừng. |
| 8g | JWT hết hạn khi đang xem | Hệ thống tự động refresh token ở background. Nếu refresh thất bại: hiển thị modal "Phiên đăng nhập hết hạn", yêu cầu đăng nhập lại. |

**Điều kiện kết thúc (Post-condition):**
- Tiến độ xem được lưu (vị trí, % hoàn thành).
- Bài giảng được đánh dấu "Đã hoàn thành" nếu xem đủ (≥ 90% thời lượng).
- Tiến độ khóa học được cập nhật.

---

### UC-09: Phụ đề đồng bộ theo thời gian thực

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-09 |
| **Tên** | Phụ đề đồng bộ theo thời gian thực |
| **Actor** | Học viên |
| **Mô tả ngắn** | Hiển thị phụ đề tự động (sinh từ AI STT — Whisper) đồng bộ với video đang phát. Học viên có thể bật/tắt phụ đề. |
| **Màn hình liên quan** | M-12 (Trình phát video bài giảng) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đang xem video bài giảng (UC-08 đang hoạt động).
- Transcript (phụ đề) của bài giảng đã được tạo qua pipeline STT và đã được Admin duyệt.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Hệ thống | Khi khởi tạo player (UC-08 bước 2), tải dữ liệu transcript (danh sách segments: {start_time, end_time, text}). |
| 2 | Hệ thống | Phụ đề mặc định bật. Hiển thị text phụ đề tương ứng với mốc thời gian hiện tại của video, cập nhật real-time khi video phát. |
| 3 | Học viên | (Tùy chọn) Nhấn nút bật/tắt phụ đề trên player control. |
| 4 | Hệ thống | Cập nhật trạng thái hiển thị phụ đề theo lựa chọn của học viên. Lưu preference. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 9a | Transcript chưa sẵn sàng (pipeline chưa hoàn tất hoặc lỗi) | Nút phụ đề bị disable. Tooltip: "Phụ đề chưa sẵn sàng cho bài giảng này." |
| 9b | Khi học viên tua video (seek) | Phụ đề tự động cập nhật theo vị trí mới. |

**Điều kiện kết thúc (Post-condition):**
- Phụ đề hiển thị đồng bộ chính xác với nội dung video.
- Preference bật/tắt phụ đề được lưu cho lần xem tiếp theo.

---

### UC-10: Đặt câu hỏi cho AI Trợ giảng (RAG Q&A)

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-10 |
| **Tên** | Đặt câu hỏi cho AI Trợ giảng (RAG Q&A) |
| **Actor** | Học viên |
| **Mô tả ngắn** | Trong khi xem video bài giảng, học viên đặt câu hỏi cho AI Trợ giảng. AI trả lời dựa trên ngữ cảnh bài giảng (transcript + slide) thông qua RAG pipeline (Retrieval-Augmented Generation). Câu trả lời kèm nguồn trích dẫn (đoạn transcript liên quan). |
| **Màn hình liên quan** | M-13 (Khung Chat AI Trợ giảng) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đang xem video bài giảng (UC-08 đang hoạt động).
- Bài giảng đã được xử lý hoàn tất qua pipeline: STT → Vector Indexing (transcript đã được embed thành vectors và lưu trong pgvector).
- Cấu hình API key AI (OpenAI/Gemini) đã được thiết lập.
- Học viên chưa vượt giới hạn số câu hỏi AI/ngày (nếu có cấu hình).

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Tại M-12 (Trình phát video), nhấn nút "Hỏi AI" → Mở panel Chat AI (M-13) dạng Bottom Sheet. |
| 2 | Hệ thống | Hiển thị M-13: khu vực chat (ban đầu trống hoặc hiển thị lịch sử chat trước đó của bài giảng này), ô nhập câu hỏi, gợi ý 3-4 câu hỏi mẫu (VD: "Giải thích khái niệm X trong bài này", "Tóm tắt phần vừa giảng"). |
| 3 | Học viên | Nhập câu hỏi vào ô nhập (hoặc chọn câu hỏi gợi ý) và nhấn "Gửi". |
| 4 | Hệ thống | Hiển thị câu hỏi trong chat bubble (phía học viên). Hiển thị typing indicator ("AI đang trả lời..."). |
| 5 | Hệ thống (Backend) | **RAG Pipeline xử lý:** (a) Nhận câu hỏi + context (lesson_id, current_timestamp). (b) Embed câu hỏi thành vector (Text Embedding model). (c) Tìm kiếm các đoạn transcript tương đồng nhất trong pgvector (similarity search, top-k = 5). (d) Xây dựng prompt với ngữ cảnh: câu hỏi + các đoạn transcript liên quan + metadata bài giảng. (e) Gọi LLM (GPT-4o-mini / Gemini Flash) sinh câu trả lời. |
| 6 | Hệ thống | Hiển thị câu trả lời AI trong chat bubble (phía AI): nội dung trả lời bằng văn bản, danh sách nguồn trích dẫn: từng đoạn transcript liên quan kèm mốc thời gian (VD: "Xem tại 05:32 – 06:15"). |
| 7 | Học viên | (Tùy chọn) Nhấn vào nguồn trích dẫn → Video tua đến mốc thời gian tương ứng. |
| 8 | Học viên | Tiếp tục đặt câu hỏi tiếp theo (quay lại bước 3), hoặc đóng panel Chat AI để quay lại xem video. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 10a | AI không thể trả lời (LLM timeout > 30 giây) | Hiển thị thông báo "AI đang gặp sự cố. Vui lòng thử lại sau." Nút "Thử lại" — gửi lại câu hỏi. |
| 10b | Lỗi server / API AI | Hiển thị Error State: thông báo lỗi cụ thể + nút "Thử lại". |
| 10c | Vượt giới hạn câu hỏi AI/ngày | Hiển thị thông báo "Bạn đã sử dụng hết lượt hỏi AI hôm nay ([X]/[Y] câu). Vui lòng quay lại vào ngày mai." Vô hiệu hóa ô nhập. |
| 10d | Bài giảng chưa có vector index (pipeline chưa hoàn tất) | Hiển thị thông báo "Chức năng AI chưa sẵn sàng cho bài giảng này." Nút Chat AI bị disable. |
| 10e | Câu hỏi trống hoặc quá ngắn (< 5 ký tự) | Hiển thị thông báo inline "Vui lòng nhập câu hỏi đầy đủ hơn." |
| 10f | Câu hỏi không liên quan đến bài giảng | AI trả lời: "Câu hỏi này không nằm trong phạm vi bài giảng. Vui lòng hỏi về nội dung bài học hiện tại." (Prompt engineering + guardrails). |

**Điều kiện kết thúc (Post-condition):**
- Câu trả lời AI được hiển thị kèm nguồn trích dẫn.
- Lịch sử chat được lưu gắn với bài giảng và học viên.
- Số câu hỏi AI của học viên trong ngày được cập nhật (tăng 1).
- Dữ liệu câu hỏi được ghi nhận để phục vụ thống kê (UC-35).

---

### UC-11: Tóm tắt bài giảng bằng AI

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-11 |
| **Tên** | Tóm tắt bài giảng bằng AI |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên yêu cầu AI tóm tắt ý chính của toàn bộ bài giảng hoặc một chương cụ thể. Hệ thống sử dụng transcript bài giảng và LLM để sinh bản tóm tắt dạng văn bản. |
| **Màn hình liên quan** | M-14 (Kết quả tóm tắt bài giảng — AI) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đang xem video bài giảng (UC-08 đang hoạt động).
- Transcript bài giảng đã sẵn sàng (pipeline STT hoàn tất).
- Cấu hình API key AI đã được thiết lập.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Tại M-12 (Trình phát video), nhấn nút "Tóm tắt bài giảng". |
| 2 | Hệ thống | Hiển thị tùy chọn: "Tóm tắt toàn bộ bài giảng" hoặc chọn chương cụ thể (nếu bài giảng có nhiều chương). |
| 3 | Học viên | Chọn phạm vi tóm tắt (toàn bộ hoặc chương cụ thể). |
| 4 | Hệ thống | Hiển thị M-14 (Modal/Bottom Sheet) với Loading State: skeleton + "AI đang tạo bản tóm tắt...". |
| 5 | Hệ thống (Backend) | Lấy transcript tương ứng (toàn bộ hoặc theo chương). Xây dựng prompt tóm tắt + transcript. Gọi LLM (GPT-4o-mini / Gemini Flash) sinh bản tóm tắt. |
| 6 | Hệ thống | Hiển thị kết quả tóm tắt trên M-14: tiêu đề (tên bài giảng / chương), nội dung tóm tắt (các ý chính, bullet points), (tùy chọn) các mốc thời gian đáng chú ý. |
| 7 | Học viên | Đọc bản tóm tắt. Đóng modal để quay lại xem video. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 11a | LLM timeout hoặc lỗi | Hiển thị thông báo "Không thể tạo bản tóm tắt. Vui lòng thử lại." Nút "Thử lại". |
| 11b | Transcript quá ngắn (< 100 từ) | Hiển thị thông báo "Nội dung bài giảng quá ngắn để tóm tắt." |
| 11c | Bản tóm tắt đã được tạo trước đó (cache) | Hiển thị ngay bản tóm tắt đã cache, kèm nút "Tạo lại" nếu học viên muốn phiên bản mới. |

**Điều kiện kết thúc (Post-condition):**
- Bản tóm tắt được hiển thị cho học viên.
- Bản tóm tắt được cache để phục vụ lần truy cập tiếp theo (giảm gọi API).
- Dữ liệu sử dụng chức năng AI được ghi nhận cho thống kê.

---

### UC-12: Chia chương bài học

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-12 |
| **Tên** | Chia chương bài học |
| **Actor** | Học viên |
| **Mô tả ngắn** | Hiển thị cấu trúc chương/mục của bài giảng. Học viên nhấn vào chương để nhảy trực tiếp đến mốc thời gian tương ứng trong video. |
| **Màn hình liên quan** | M-12 (Trình phát video bài giảng — sidebar/drawer chương) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đang xem video bài giảng (UC-08 đang hoạt động).
- Bài giảng đã được Admin thiết lập cấu trúc chương với mốc thời gian.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Hệ thống | Khi khởi tạo player, tải danh sách chương (chapters) kèm mốc thời gian. Hiển thị markers trên seekbar. |
| 2 | Học viên | Nhấn nút "Danh sách chương" hoặc mở sidebar chương. |
| 3 | Hệ thống | Hiển thị danh sách chương: tên chương, mốc thời gian bắt đầu, trạng thái (đang xem / đã xem / chưa xem). Highlight chương hiện tại. |
| 4 | Học viên | Nhấn vào một chương → Video tua đến mốc thời gian tương ứng. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 12a | Bài giảng không có chương (chưa thiết lập) | Ẩn nút danh sách chương. Không hiển thị markers trên seekbar. |

**Điều kiện kết thúc (Post-condition):**
- Video nhảy đến mốc thời gian của chương được chọn.
- Chương hiện tại được highlight trong danh sách.

---

### UC-13: Ghi chú theo mốc thời gian video

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-13 |
| **Tên** | Ghi chú theo mốc thời gian video |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên tạo ghi chú gắn với mốc thời gian cụ thể của video. Sau đó có thể xem lại danh sách ghi chú và nhấn vào để nhảy đến đúng thời điểm trong video. |
| **Màn hình liên quan** | M-15 (Danh sách ghi chú), M-16 (Tạo / Sửa ghi chú) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đang xem video bài giảng (UC-08 đang hoạt động).
- Học viên đã enrolled trong khóa học.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Tại M-12 (Trình phát video), nhấn nút "Ghi chú" tại thời điểm muốn ghi nhận. |
| 2 | Hệ thống | Tự động pause video. Mở M-16 (Form tạo ghi chú) với mốc thời gian hiện tại được pre-fill (VD: "Ghi chú tại 12:34"). |
| 3 | Học viên | Nhập nội dung ghi chú và nhấn "Lưu". |
| 4 | Hệ thống | Lưu ghi chú vào cơ sở dữ liệu (gắn lesson_id, user_id, timestamp, content). Hiển thị toast "Đã lưu ghi chú." Video tiếp tục phát. |
| 5 | Học viên | (Sau này) Nhấn nút "Xem danh sách ghi chú" → Mở M-15. |
| 6 | Hệ thống | Hiển thị danh sách ghi chú sắp xếp theo mốc thời gian: mốc thời gian, nội dung (truncate), nút sửa/xóa. |
| 7 | Học viên | Nhấn vào một ghi chú → Video tua đến mốc thời gian tương ứng. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 13a | Chưa có ghi chú nào | Hiển thị Empty State: "Chưa có ghi chú nào. Hãy tạo ghi chú đầu tiên!" với hướng dẫn. |
| 13b | Sửa ghi chú | Học viên nhấn nút sửa → Mở M-16 với nội dung pre-fill → Chỉnh sửa và lưu. |
| 13c | Xóa ghi chú | Học viên nhấn nút xóa → Hiển thị dialog xác nhận → Xác nhận: xóa ghi chú khỏi CSDL. |
| 13d | Offline | Ghi chú được lưu cục bộ, đồng bộ lên server khi có mạng. |

**Điều kiện kết thúc (Post-condition):**
- Ghi chú được lưu/sửa/xóa thành công trong cơ sở dữ liệu.
- Ghi chú gắn chính xác với mốc thời gian và bài giảng tương ứng.

---

### UC-14: Làm bài kiểm tra giữa video (Quiz)

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-14 |
| **Tên** | Làm bài kiểm tra giữa video (Quiz) |
| **Actor** | Học viên |
| **Mô tả ngắn** | Câu hỏi kiểm tra trắc nghiệm xuất hiện tự động tại các mốc thời gian định sẵn trong video. Học viên trả lời ngay và xem kết quả đúng/sai trước khi tiếp tục video. |
| **Màn hình liên quan** | M-17 (Làm Quiz giữa video — Modal/Overlay) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đang xem video bài giảng (UC-08 đang hoạt động).
- Bài giảng đã được Admin gán câu hỏi quiz tại các mốc thời gian cụ thể.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Hệ thống | Video phát đến mốc thời gian có quiz → Tự động pause video. |
| 2 | Hệ thống | Hiển thị M-17 (overlay quiz): câu hỏi trắc nghiệm, các phương án lựa chọn (A, B, C, D). |
| 3 | Học viên | Chọn đáp án và nhấn "Trả lời". |
| 4 | Hệ thống | Hiển thị kết quả ngay lập tức: đúng (✅ highlight xanh) hoặc sai (❌ highlight đỏ + hiển thị đáp án đúng). Hiển thị giải thích (nếu có). |
| 5 | Học viên | Nhấn "Tiếp tục" → Đóng overlay quiz, video tiếp tục phát. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 14a | Học viên đã trả lời câu quiz này trước đó (xem lại video) | Không hiển thị quiz lần thứ hai (hoặc hiển thị với trạng thái "Đã trả lời" + kết quả trước đó). Tùy cấu hình Admin. |
| 14b | Quiz có nhiều câu tại cùng một mốc | Hiển thị từng câu tuần tự (câu 1/3, 2/3, 3/3). |

**Điều kiện kết thúc (Post-condition):**
- Kết quả trả lời quiz được ghi nhận (đúng/sai, đáp án chọn, thời gian trả lời).
- Video tiếp tục phát sau khi hoàn thành quiz.

---

### UC-15: Làm bài tập trắc nghiệm / tự luận

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-15 |
| **Tên** | Làm bài tập trắc nghiệm / tự luận |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên làm bài tập cuối bài/cuối khóa (trắc nghiệm hoặc tự luận). Xem kết quả chấm điểm tự động (trắc nghiệm) hoặc chờ chấm (tự luận). |
| **Màn hình liên quan** | M-18 (Làm bài tập cuối bài), M-19 (Kết quả bài tập) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã đăng nhập và enrolled trong khóa học.
- Bài tập đã được Admin tạo và gán vào bài giảng.
- (Tùy cấu hình) Học viên đã hoàn thành xem video bài giảng liên quan.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Từ M-09 (Chi tiết khóa học) hoặc sau khi xem xong video, chọn "Làm bài tập". |
| 2 | Hệ thống | Gọi API lấy bài tập (GET /api/exercises/{id}). Hiển thị M-18: tên bài tập, số câu hỏi, thời gian làm bài (nếu có), nút "Bắt đầu". |
| 3 | Học viên | Nhấn "Bắt đầu" → Hệ thống bắt đầu đếm thời gian (nếu có giới hạn). |
| 4 | Hệ thống | Hiển thị câu hỏi lần lượt: trắc nghiệm (chọn đáp án) hoặc tự luận (ô nhập text). Thanh tiến trình (câu hiện tại / tổng câu). |
| 5 | Học viên | Trả lời từng câu, nhấn "Câu tiếp theo" hoặc chuyển qua lại giữa các câu. |
| 6 | Học viên | Hoàn thành tất cả câu hỏi → nhấn "Nộp bài". |
| 7 | Hệ thống | Hiển thị dialog xác nhận "Bạn có chắc muốn nộp bài?" |
| 8 | Học viên | Xác nhận nộp. |
| 9 | Hệ thống | **Trắc nghiệm:** Chấm điểm tự động, so sánh đáp án. **Tự luận:** Ghi nhận bài làm, trạng thái "Chờ chấm". |
| 10 | Hệ thống | Hiển thị M-19 (Kết quả): điểm số, số câu đúng/sai, chi tiết từng câu (đáp án đúng, giải thích). Nếu tự luận: hiển thị "Bài của bạn đã được gửi. Kết quả sẽ được cập nhật sau." |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 15a | Hết thời gian làm bài | Tự động nộp bài. Hiển thị thông báo "Đã hết thời gian, bài của bạn đã được nộp tự động." |
| 15b | Không đạt điểm tối thiểu | Hiển thị kết quả + thông báo "Chưa đạt yêu cầu ([X] điểm / [Y] điểm cần)." Nút "Làm lại" (nếu Admin cho phép). |
| 15c | Vượt số lần làm lại cho phép | Hiển thị "Bạn đã sử dụng hết số lần làm bài." Chỉ hiển thị kết quả, không cho làm lại. |
| 15d | Mất kết nối khi đang làm bài | Lưu đáp án vào cache cục bộ, đồng bộ và nộp khi có mạng. |

**Điều kiện kết thúc (Post-condition):**
- Kết quả bài tập được lưu (điểm, đáp án, thời gian làm).
- Tiến độ khóa học được cập nhật.
- (Trắc nghiệm) Điểm số hiển thị ngay.
- (Tự luận) Bài làm được lưu với trạng thái "Chờ chấm".

---

### UC-16: Theo dõi tiến độ học tập

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-16 |
| **Tên** | Theo dõi tiến độ học tập |
| **Actor** | Học viên |
| **Mô tả ngắn** | Hiển thị tiến độ hoàn thành từng bài giảng, từng khóa học (% video đã xem, bài tập đã làm). Tự động lưu vị trí xem video dở. |
| **Màn hình liên quan** | M-20 (Tiến độ học tập) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã đăng nhập.
- Học viên đã enrolled ít nhất 1 khóa học.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Truy cập tab "Tiến độ" hoặc mở M-20 từ bottom navigation. |
| 2 | Hệ thống | Gọi API lấy tiến độ (GET /api/progress/me). Hiển thị tổng quan: tổng khóa học đã đăng ký, tổng thời lượng học, danh sách khóa học kèm progress bar (%), bài giảng tiếp theo cần xem, bài tập chưa làm. |
| 3 | Học viên | Nhấn vào một khóa học → Xem chi tiết tiến độ từng bài giảng: đã xem / chưa xem, bài tập đã làm / chưa làm, điểm quiz. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 16a | Chưa có khóa học nào | Chuyển hướng hoặc gợi ý "Bạn chưa đăng ký khóa học nào. Khám phá ngay!" |

**Điều kiện kết thúc (Post-condition):**
- Học viên nắm được tiến độ học tập tổng quan và chi tiết.

---

### UC-17: Xem khóa học đã mua / Thư viện cá nhân

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-17 |
| **Tên** | Xem khóa học đã mua / Thư viện cá nhân |
| **Actor** | Học viên |
| **Mô tả ngắn** | Xem danh sách các khóa học đã mua/đăng ký, tiếp tục học từ vị trí dở dang. |
| **Màn hình liên quan** | M-21 (Khóa học của tôi — Thư viện) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đã đăng nhập.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Truy cập tab "Khóa học của tôi" từ bottom navigation hoặc Trang chủ. |
| 2 | Hệ thống | Gọi API (GET /api/enrollments/me). Hiển thị M-21: danh sách khóa học đã mua dạng card: ảnh bìa, tên, tiến độ (% progress bar), bài giảng tiếp theo, nút "Tiếp tục học". |
| 3 | Học viên | Nhấn "Tiếp tục học" trên một khóa → Chuyển đến UC-08 (tại bài giảng dở dang, vị trí video dở). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 17a | Chưa mua khóa học nào | Hiển thị Empty State: illustration + nút "Khám phá khóa học". |

**Điều kiện kết thúc (Post-condition):**
- Học viên xem được danh sách khóa đã mua và tiếp tục học.

---

### UC-20: Đăng xuất (Học viên)

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-20 |
| **Tên** | Đăng xuất |
| **Actor** | Học viên |
| **Mô tả ngắn** | Học viên đăng xuất khỏi ứng dụng, xóa phiên đăng nhập. |
| **Màn hình liên quan** | M-23 (Hồ sơ cá nhân) |

**Điều kiện tiên quyết (Pre-condition):**
- Học viên đang đăng nhập (có phiên hoạt động).

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Học viên | Tại M-23 (Hồ sơ cá nhân), nhấn nút "Đăng xuất". |
| 2 | Hệ thống | Hiển thị dialog xác nhận "Bạn có chắc muốn đăng xuất?" |
| 3 | Học viên | Xác nhận đăng xuất. |
| 4 | Hệ thống | Gọi API thu hồi refresh token (POST /api/auth/logout). Xóa JWT token và refresh token khỏi EncryptedSharedPreferences. Xóa dữ liệu cache phiên đăng nhập. |
| 5 | Hệ thống | Chuyển về màn hình Đăng nhập (M-03). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 20a | Học viên nhấn "Hủy" | Đóng dialog, quay lại M-23. Không thay đổi. |
| 20b | Lỗi API khi logout (mất mạng) | Vẫn xóa token cục bộ, đăng xuất khỏi app. Token sẽ tự hết hạn trên server. |

**Điều kiện kết thúc (Post-condition):**
- Phiên đăng nhập bị xóa trên cả client và server.
- Học viên phải đăng nhập lại để sử dụng ứng dụng.

---

### UC-23: Đăng nhập Admin

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-23 |
| **Tên** | Đăng nhập Admin |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Quản trị viên đăng nhập vào hệ thống quản trị (Web Admin) bằng tài khoản admin. Hệ thống xác thực JWT, kiểm tra phân quyền admin, và chuyển đến Dashboard tổng quan. |
| **Màn hình liên quan** | A-01 (Đăng nhập Admin) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên có tài khoản với role "admin" trong hệ thống.
- Trình duyệt có kết nối internet.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Truy cập URL Web Admin (VD: admin.example.com). |
| 2 | Hệ thống | Kiểm tra JWT token trong cookie/localStorage. Nếu không có hoặc hết hạn → Hiển thị A-01 (Form đăng nhập). |
| 3 | Quản trị viên | Nhập email và mật khẩu, nhấn "Đăng nhập". |
| 4 | Hệ thống | Gọi API xác thực (POST /api/auth/login). Backend kiểm tra: email + mật khẩu đúng, tài khoản có role "admin". |
| 5 | Hệ thống | Xác thực thành công → Nhận JWT access token + refresh token. Lưu vào httpOnly cookie (hoặc localStorage). |
| 6 | Hệ thống | Redirect đến Dashboard tổng quan (A-02). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 23a | Token hợp lệ tồn tại (bước 2) | Redirect thẳng đến Dashboard (A-02), bỏ qua đăng nhập. |
| 23b | Email hoặc mật khẩu sai | Hiển thị inline error "Thông tin đăng nhập không đúng." |
| 23c | Tài khoản không có quyền admin | Hiển thị "Tài khoản không có quyền truy cập trang quản trị." |
| 23d | Tài khoản bị khóa | Hiển thị "Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên cấp trên." |
| 23e | Phiên đăng nhập hết hạn (trong khi sử dụng) | Auto-redirect về A-01 + thông báo "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại." |

**Điều kiện kết thúc (Post-condition):**
- Quản trị viên được xác thực và phân quyền.
- JWT token được lưu an toàn trên trình duyệt.
- Quản trị viên có quyền truy cập toàn bộ chức năng quản trị.

---

### UC-24: Xem Dashboard tổng quan

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-24 |
| **Tên** | Xem Dashboard tổng quan |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Trang tổng quan hiển thị các chỉ số chính của hệ thống: tổng doanh thu, số học viên, số khóa học, số câu hỏi AI, video đang xử lý pipeline. Biểu đồ xu hướng theo thời gian. |
| **Màn hình liên quan** | A-02 (Dashboard tổng quan) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập (UC-23).

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Hệ thống | Sau khi đăng nhập hoặc nhấn menu "Dashboard" → Hiển thị A-02. |
| 2 | Hệ thống | Gọi các API thống kê tổng hợp song song. Hiển thị các widget: Tổng doanh thu (ngày/tuần/tháng), Tổng số học viên + mới đăng ký, Tổng số khóa học (đã xuất bản / nháp), Số câu hỏi AI (ngày/tuần/tháng), Video đang xử lý pipeline (số lượng, trạng thái). Biểu đồ xu hướng: doanh thu, học viên mới, câu hỏi AI theo thời gian. |
| 3 | Quản trị viên | Xem tổng quan. (Tùy chọn) Nhấn vào widget để truy cập chi tiết (VD: nhấn widget doanh thu → UC-33). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 24a | Đang tải dữ liệu | Hiển thị skeleton cho từng widget + biểu đồ. |
| 24b | Lỗi API | Hiển thị widget với trạng thái lỗi + nút "Thử lại" cho từng widget riêng biệt. |

**Điều kiện kết thúc (Post-condition):**
- Quản trị viên nắm được tình hình tổng quan hệ thống qua các chỉ số chính.

---

### UC-25: Quản lý khóa học (CRUD)

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-25 |
| **Tên** | Quản lý khóa học (CRUD) |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Tạo mới, chỉnh sửa, xóa, ẩn/hiện khóa học. Thiết lập thông tin: tên, mô tả, giá, danh mục, ảnh bìa, trạng thái xuất bản. |
| **Màn hình liên quan** | A-03 (Danh sách khóa học), A-04 (Tạo / Chỉnh sửa khóa học) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập.

**Luồng chính (Main Flow) — Tạo khóa học:**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Tại A-03 (Danh sách khóa học), nhấn nút "Tạo khóa học mới". |
| 2 | Hệ thống | Hiển thị A-04 (Form tạo khóa học): tên, mô tả (rich text editor), danh mục (dropdown — từ UC-36), giá, ảnh bìa (upload), trạng thái (Nháp / Đã xuất bản / Ẩn). |
| 3 | Quản trị viên | Nhập đầy đủ thông tin, upload ảnh bìa, nhấn "Lưu". |
| 4 | Hệ thống | Validate: tên bắt buộc, giá ≥ 0, ảnh bìa đúng định dạng. |
| 5 | Hệ thống | Lưu khóa học vào CSDL. Hiển thị toast "Tạo khóa học thành công." Redirect về A-03. |

**Luồng chính — Chỉnh sửa khóa học:**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Tại A-03, nhấn nút "Sửa" trên một khóa học. |
| 2 | Hệ thống | Hiển thị A-04 với dữ liệu pre-fill. |
| 3 | Quản trị viên | Chỉnh sửa thông tin, nhấn "Lưu". |
| 4 | Hệ thống | Cập nhật CSDL. Toast "Cập nhật thành công." Redirect về A-03. |

**Luồng chính — Xóa khóa học:**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Tại A-03, nhấn nút "Xóa" trên một khóa học. |
| 2 | Hệ thống | Hiển thị modal xác nhận destructive: "Bạn có chắc muốn xóa khóa học [tên]? Hành động này không thể hoàn tác." |
| 3 | Quản trị viên | Xác nhận xóa. |
| 4 | Hệ thống | Soft-delete khóa học (đánh dấu deleted, không xóa vật lý). Toast "Đã xóa khóa học." Cập nhật danh sách. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 25a | Validate lỗi (tên trống, giá âm, ảnh sai format) | Hiển thị inline error per field. |
| 25b | Xóa khóa học đã có học viên enrolled | Hiển thị cảnh báo: "Khóa học này đã có [N] học viên đăng ký. Nên ẩn thay vì xóa." Gợi ý dùng trạng thái "Ẩn". |
| 25c | Chưa có khóa học nào | Empty State: illustration + nút CTA "Tạo khóa học đầu tiên". |

**Điều kiện kết thúc (Post-condition):**
- Khóa học được tạo/cập nhật/xóa thành công trong CSDL.
- Danh sách khóa học trên A-03 được cập nhật.

---

### UC-26: Quản lý cấu trúc bài giảng

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-26 |
| **Tên** | Quản lý cấu trúc bài giảng |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Tạo và sắp xếp cấu trúc bài giảng trong khóa học: chương, bài, thứ tự. Gắn video, bài tập, tài liệu vào từng bài. |
| **Màn hình liên quan** | A-05 (Chi tiết khóa học + Cấu trúc bài giảng), A-06 (Tạo / Chỉnh sửa bài giảng) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập.
- Khóa học đã tồn tại (UC-25).

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Tại A-03, nhấn vào khóa học → Mở A-05 (Chi tiết + Cấu trúc). |
| 2 | Hệ thống | Hiển thị cấu trúc hiện tại: danh sách chương → bài giảng (dạng tree, hỗ trợ drag-and-drop sắp xếp). |
| 3 | Quản trị viên | Thêm chương mới: nhấn "Thêm chương" → Nhập tên chương → Lưu. |
| 4 | Quản trị viên | Thêm bài giảng vào chương: nhấn "Thêm bài giảng" → Mở A-06 (Form bài giảng): tên, mô tả, upload video (UC-27), gắn bài tập/quiz, thiết lập mốc thời gian chương. |
| 5 | Quản trị viên | Drag-and-drop để sắp xếp thứ tự chương và bài giảng. |
| 6 | Hệ thống | Cập nhật thứ tự trong CSDL khi drop. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 26a | Xóa chương có bài giảng | Hiển thị cảnh báo: "Chương này có [N] bài giảng. Xóa chương sẽ xóa toàn bộ bài giảng bên trong." Modal xác nhận. |
| 26b | Xóa bài giảng đã có video/bài tập | Modal xác nhận kèm danh sách tài nguyên liên quan sẽ bị ảnh hưởng. |

**Điều kiện kết thúc (Post-condition):**
- Cấu trúc chương/bài giảng được cập nhật trong CSDL.
- Thứ tự hiển thị trên Mobile App phản ánh đúng cấu trúc Admin thiết lập.

---

### UC-27: Upload video bài giảng

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-27 |
| **Tên** | Upload video bài giảng |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Upload file video bài giảng lên hệ thống. Hiển thị tiến trình upload, hỗ trợ nhiều định dạng video. Sau khi upload thành công, tự động trigger pipeline xử lý video (UC-28). |
| **Màn hình liên quan** | A-06 (Tạo / Chỉnh sửa bài giảng), A-07 (Upload video & Trạng thái Pipeline) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập.
- Khóa học và chương/bài giảng đã tồn tại.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Tại A-06 hoặc A-07, sử dụng vùng upload video (drag-and-drop hoặc click chọn file). |
| 2 | Hệ thống | Validate file: kiểm tra định dạng (MP4, MOV, AVI, MKV, WEBM), dung lượng (≤ 5 GB), codec hợp lệ. |
| 3 | Hệ thống | Bắt đầu upload file lên storage (Cloudflare Stream / AWS S3). Hiển thị thanh tiến trình upload (%). |
| 4 | Hệ thống | Upload hoàn tất → Lưu metadata video vào CSDL (filename, size, duration, storage URL). Cập nhật trạng thái: "Đã upload". |
| 5 | Hệ thống | Tự động trigger pipeline xử lý video (UC-28): Upload ✓ → STT (khởi động) → Vector Indexing (chờ). |
| 6 | Hệ thống | Hiển thị toast "Upload thành công. Pipeline xử lý đã bắt đầu." |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 27a | File không hợp lệ (sai định dạng, quá lớn) | Hiển thị thông báo "File không hợp lệ: [lý do]. Vui lòng chọn file video đúng định dạng." |
| 27b | Upload bị gián đoạn (mất mạng) | Hỗ trợ resumable upload. Hiển thị "Upload bị gián đoạn. Nhấn để tiếp tục." |
| 27c | Upload thay thế video cũ | Hiển thị cảnh báo: "Video cũ sẽ bị thay thế. Transcript và vector index hiện tại sẽ bị xóa và xử lý lại." Modal xác nhận. |

**Điều kiện kết thúc (Post-condition):**
- Video được lưu trữ thành công trên cloud storage.
- Metadata video được ghi nhận trong CSDL.
- Pipeline xử lý tự động được trigger.

---

### UC-28: Xử lý video tự động — Pipeline (STT → Vector Indexing)

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-28 |
| **Tên** | Xử lý video tự động — Pipeline (STT → Vector Indexing) |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Theo dõi và quản lý pipeline xử lý video tự động: Upload → Speech-to-Text (Whisper) → Vector Indexing (Embedding). Hiển thị trạng thái từng bước, cho phép xử lý lại nếu lỗi. Đây là chức năng cốt lõi cho toàn bộ hệ thống AI Trợ giảng. |
| **Màn hình liên quan** | A-07 (Upload video & Trạng thái Pipeline) |

**Điều kiện tiên quyết (Pre-condition):**
- Video đã được upload thành công (UC-27).
- Cấu hình Whisper API và Text Embedding model đã được thiết lập.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Hệ thống | Sau khi video upload thành công, tự động khởi động pipeline. Hiển thị trên A-07 bảng trạng thái pipeline: **Tên video → Upload ✓ → STT (đang xử lý ⏳) → Vector Index (chờ ⏸)**. |
| 2 | Hệ thống (Backend) | **Bước STT (Speech-to-Text):** Trích xuất audio từ video. Gọi Whisper API phiên âm audio → transcript (danh sách segments: {start_time, end_time, text}). Lưu transcript vào CSDL. Cập nhật trạng thái: **STT ✓**. |
| 3 | Hệ thống (Backend) | **Bước Vector Indexing:** Chia transcript thành chunks (mỗi chunk ~500 tokens, overlap 50 tokens). Gọi Text Embedding API embed từng chunk thành vector. Lưu vectors vào pgvector (table: lesson_embeddings). Cập nhật trạng thái: **Vector Index ✓**. |
| 4 | Hệ thống | Cập nhật trạng thái pipeline trên A-07: **Upload ✓ → STT ✓ → Vector Index ✓**. Hiển thị badge "Hoàn tất" (xanh). |
| 5 | Quản trị viên | Xem trạng thái pipeline hoàn tất. Có thể chuyển sang UC-29 (Duyệt/Chỉnh sửa Transcript) để review kết quả STT. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 28a | STT thất bại (Whisper API lỗi, audio không rõ) | Cập nhật trạng thái: **STT ✗** (badge đỏ). Hiển thị thông báo lỗi chi tiết (VD: "Whisper API timeout", "Audio quality too low"). Nút **"Xử lý lại"** — retry bước STT. Pipeline dừng tại bước này (Vector Index không chạy). |
| 28b | Vector Indexing thất bại (Embedding API lỗi) | Cập nhật trạng thái: **Vector Index ✗** (badge đỏ). Hiển thị thông báo lỗi. Nút **"Xử lý lại"** — retry bước Vector Index (không cần chạy lại STT). |
| 28c | Quản trị viên chỉnh sửa transcript (UC-29) sau khi pipeline hoàn tất | Sau khi lưu transcript đã chỉnh sửa → Tự động trigger lại bước Vector Indexing (re-embed transcript mới). |
| 28d | Xử lý đang chạy — Admin muốn hủy | Nút "Hủy xử lý" → Dừng pipeline, trạng thái chuyển về "Đã upload" (cần chạy lại toàn bộ). |

**Điều kiện kết thúc (Post-condition):**
- Transcript (phụ đề) được tạo và lưu trong CSDL.
- Vectors (embeddings) của transcript được lưu trong pgvector.
- Video sẵn sàng cho: phát HLS trên Mobile, AI Trợ giảng Q&A (UC-10), phụ đề đồng bộ (UC-09), tóm tắt AI (UC-11).

---

### UC-29: Duyệt / Chỉnh sửa phụ đề (Transcript)

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-29 |
| **Tên** | Duyệt / Chỉnh sửa phụ đề (Transcript) |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Xem và chỉnh sửa kết quả phiên âm tự động (transcript) từ STT. Đồng bộ phụ đề với timeline video. |
| **Màn hình liên quan** | A-08 (Duyệt / Chỉnh sửa Transcript) |

**Điều kiện tiên quyết (Pre-condition):**
- Pipeline STT đã hoàn tất thành công cho video này (UC-28 bước 2).

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Từ A-07 hoặc A-05, nhấn "Xem Transcript" cho một video. |
| 2 | Hệ thống | Hiển thị A-08: bên trái — video preview player, bên phải — danh sách dòng transcript theo mốc thời gian ({start_time – end_time}: text). Highlight dòng đang phát. |
| 3 | Quản trị viên | Nhấn vào một dòng transcript → Video tua đến mốc tương ứng để review. |
| 4 | Quản trị viên | Chỉnh sửa nội dung text của dòng transcript (inline edit). Chỉnh sửa mốc thời gian (start/end) nếu cần. |
| 5 | Quản trị viên | Nhấn "Lưu" → Hệ thống cập nhật transcript trong CSDL. |
| 6 | Hệ thống | Nếu nội dung text thay đổi → Tự động trigger re-indexing (re-embed vectors) ở background. Hiển thị thông báo "Transcript đã cập nhật. Vector index đang được xử lý lại." |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 29a | Transcript chất lượng kém (nhiều lỗi STT) | Admin chỉnh sửa toàn bộ. Hoặc nhấn "Xử lý lại STT" để chạy lại Whisper. |

**Điều kiện kết thúc (Post-condition):**
- Transcript được cập nhật chính xác trong CSDL.
- Vector index được re-embed nếu nội dung thay đổi.
- Phụ đề trên Mobile App phản ánh nội dung đã chỉnh sửa.

---

### UC-30: Quản lý ngân hàng đề thi

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-30 |
| **Tên** | Quản lý ngân hàng đề thi |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Tạo, chỉnh sửa, xóa câu hỏi trắc nghiệm/tự luận. Phân loại theo bài giảng/chương/độ khó. Tạo bộ đề thi/quiz từ ngân hàng câu hỏi. |
| **Màn hình liên quan** | A-09 (Danh sách câu hỏi), A-10 (Tạo / Chỉnh sửa câu hỏi), A-11 (Tạo bộ đề thi/Quiz) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập.
- (Để gắn câu hỏi với bài giảng) Khóa học và bài giảng đã tồn tại.

**Luồng chính (Main Flow) — Tạo câu hỏi:**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Tại A-09 (Danh sách câu hỏi), nhấn "Tạo câu hỏi mới". |
| 2 | Hệ thống | Hiển thị A-10 (Form): loại (trắc nghiệm / tự luận), nội dung câu hỏi, phương án A-D (nếu trắc nghiệm), đáp án đúng, giải thích, độ khó (Dễ / Trung bình / Khó), gắn với bài giảng/chương (dropdown). |
| 3 | Quản trị viên | Nhập thông tin đầy đủ, nhấn "Lưu". |
| 4 | Hệ thống | Validate và lưu câu hỏi. Toast "Tạo câu hỏi thành công." Redirect về A-09. |

**Luồng chính — Tạo bộ đề:**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Tại A-09, nhấn "Tạo bộ đề thi/Quiz". |
| 2 | Hệ thống | Hiển thị A-11: form cấu hình (tên đề, bài giảng liên quan, số câu, thời gian, điểm đạt, cho phép làm lại). Danh sách câu hỏi từ ngân hàng (có filter theo bài giảng, độ khó). |
| 3 | Quản trị viên | Chọn câu hỏi (checkbox) hoặc "Chọn ngẫu nhiên [N] câu theo bộ lọc". Cấu hình tham số. Nhấn "Lưu". |
| 4 | Hệ thống | Tạo bộ đề, lưu vào CSDL. Toast thành công. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 30a | Chưa có câu hỏi nào | Empty State A-09: "Chưa có câu hỏi nào. Tạo câu hỏi đầu tiên!" |
| 30b | Xóa câu hỏi đang sử dụng trong bộ đề | Hiển thị cảnh báo: "Câu hỏi đang được sử dụng trong [N] bộ đề." Modal xác nhận. |

**Điều kiện kết thúc (Post-condition):**
- Câu hỏi / bộ đề được tạo/cập nhật/xóa trong CSDL.
- Bộ đề sẵn sàng gán vào bài giảng (UC-31).

---

### UC-31: Quản lý bài tập

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-31 |
| **Tên** | Quản lý bài tập |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Gán bài tập (quiz giữa video, bài tập cuối bài) vào bài giảng. Cấu hình điểm đạt, số lần làm lại, thời gian làm bài. |
| **Màn hình liên quan** | A-11 (Tạo bộ đề thi/Quiz), A-12 (Danh sách bài tập) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập.
- Bộ đề/câu hỏi đã được tạo trong ngân hàng (UC-30).
- Bài giảng đã tồn tại (UC-26).

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Tại A-12 hoặc A-06 (Form bài giảng), chọn "Gán bài tập / Quiz". |
| 2 | Hệ thống | Hiển thị danh sách bộ đề từ ngân hàng. |
| 3 | Quản trị viên | Chọn bộ đề cần gán. Cấu hình: loại gán (quiz giữa video — thiết lập mốc thời gian, hoặc bài tập cuối bài), điểm đạt tối thiểu, số lần làm lại cho phép, thời gian giới hạn. |
| 4 | Quản trị viên | Nhấn "Lưu". |
| 5 | Hệ thống | Lưu liên kết bài tập — bài giảng. Toast thành công. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 31a | Quiz giữa video — mốc thời gian vượt quá duration video | Hiển thị lỗi "Mốc thời gian phải nằm trong khoảng thời lượng video." |

**Điều kiện kết thúc (Post-condition):**
- Bài tập/quiz được gán vào bài giảng.
- Học viên sẽ thấy quiz tại mốc thời gian (UC-14) hoặc bài tập cuối bài (UC-15).

---

### UC-33: Quản lý doanh thu

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-33 |
| **Tên** | Quản lý doanh thu |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Xem tổng quan doanh thu, danh sách giao dịch thanh toán, lọc theo thời gian/khóa học/trạng thái. |
| **Màn hình liên quan** | A-15 (Quản lý doanh thu) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Truy cập menu "Doanh thu" → Hiển thị A-15. |
| 2 | Hệ thống | Gọi API thống kê doanh thu. Hiển thị: tổng doanh thu theo khoảng thời gian (ngày/tuần/tháng), biểu đồ doanh thu theo thời gian (line chart), bảng danh sách giao dịch: học viên, khóa học, số tiền, phương thức, trạng thái (thành công/đang xử lý/thất bại), ngày giờ. |
| 3 | Quản trị viên | (Tùy chọn) Sử dụng bộ lọc: khoảng thời gian (date picker), khóa học cụ thể, trạng thái giao dịch. |
| 4 | Hệ thống | Cập nhật dữ liệu theo bộ lọc. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 33a | Chưa có giao dịch nào | Empty State: "Chưa có giao dịch nào." Biểu đồ trống. |

**Điều kiện kết thúc (Post-condition):**
- Quản trị viên nắm được tình hình doanh thu tổng quan và chi tiết.

---

### UC-34: Xem báo cáo phân tích hành vi học viên

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-34 |
| **Tên** | Xem báo cáo phân tích hành vi học viên |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Biểu đồ và thống kê hành vi học viên: tỷ lệ hoàn thành khóa học, thời lượng xem trung bình, video có tỷ lệ bỏ dở cao, bài giảng được xem nhiều nhất, thời gian học theo ngày/tuần. |
| **Màn hình liên quan** | A-16 (Báo cáo phân tích hành vi học viên) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập.
- Có dữ liệu hành vi học viên (ít nhất có học viên đã xem video).

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Truy cập menu "Báo cáo" → "Phân tích hành vi" → Hiển thị A-16. |
| 2 | Hệ thống | Gọi API phân tích. Hiển thị dashboard charts: **Tỷ lệ hoàn thành khóa học** (bar chart — từng khóa), **Thời lượng xem trung bình** (theo khóa/bài giảng), **Top bài giảng được xem nhiều nhất** (horizontal bar), **Video có tỷ lệ bỏ dở cao** (sorted list — % bỏ ngang), **Thời gian học theo ngày/tuần** (line/area chart — xu hướng), **Retention rate** — % học viên quay lại học sau ngày đầu. |
| 3 | Quản trị viên | (Tùy chọn) Chọn bộ lọc: khóa học cụ thể, khoảng thời gian. |
| 4 | Hệ thống | Cập nhật biểu đồ theo bộ lọc. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 34a | Chưa có dữ liệu | Hiển thị thông báo "Chưa có dữ liệu phân tích. Dữ liệu sẽ xuất hiện khi có học viên bắt đầu học." |
| 34b | Đang tải biểu đồ | Skeleton charts cho từng biểu đồ. |

**Điều kiện kết thúc (Post-condition):**
- Quản trị viên nắm được xu hướng và hành vi học tập của học viên.
- Dữ liệu hỗ trợ ra quyết định cải thiện nội dung khóa học.

---

### UC-35: Xem thống kê câu hỏi AI

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-35 |
| **Tên** | Xem thống kê câu hỏi AI |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Thống kê số lượng câu hỏi AI theo thời gian, theo khóa học/bài giảng. Xem danh sách câu hỏi phổ biến nhất, đánh giá chất lượng câu trả lời AI. |
| **Màn hình liên quan** | A-17 (Thống kê câu hỏi AI) |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đã đăng nhập.
- Có dữ liệu câu hỏi AI từ học viên.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Truy cập menu "Báo cáo" → "Thống kê AI" → Hiển thị A-17. |
| 2 | Hệ thống | Gọi API thống kê AI. Hiển thị: **Số câu hỏi AI theo thời gian** (line chart — ngày/tuần/tháng), **Số câu hỏi theo khóa học/bài giảng** (bar chart), **Top câu hỏi phổ biến nhất** (bảng danh sách: câu hỏi, số lần hỏi, bài giảng liên quan), **Đánh giá chất lượng** (nếu có feedback từ học viên — % hài lòng/không hài lòng), **Tổng chi phí API AI** (ước tính). |
| 3 | Quản trị viên | (Tùy chọn) Lọc theo khóa học, bài giảng, khoảng thời gian. |
| 4 | Quản trị viên | Nhấn vào câu hỏi phổ biến → Xem chi tiết: nội dung câu hỏi, câu trả lời AI, nguồn trích dẫn, feedback. |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 35a | Chưa có dữ liệu câu hỏi AI | Hiển thị thông báo "Chưa có dữ liệu câu hỏi AI." |

**Điều kiện kết thúc (Post-condition):**
- Quản trị viên nắm được tình hình sử dụng AI Trợ giảng.
- Dữ liệu hỗ trợ đánh giá hiệu quả và tối ưu hệ thống AI.

---

### UC-38: Đăng xuất Admin

| Thuộc tính | Nội dung |
|------------|----------|
| **Mã UC** | UC-38 |
| **Tên** | Đăng xuất Admin |
| **Actor** | Quản trị viên |
| **Mô tả ngắn** | Quản trị viên đăng xuất khỏi trang quản trị. |
| **Màn hình liên quan** | Sidebar / Header navigation |

**Điều kiện tiên quyết (Pre-condition):**
- Quản trị viên đang đăng nhập.

**Luồng chính (Main Flow):**

| Bước | Actor | Hành động |
|------|-------|-----------|
| 1 | Quản trị viên | Nhấn avatar/tên trên header → Chọn "Đăng xuất". |
| 2 | Hệ thống | Gọi API logout (POST /api/auth/logout). Xóa JWT token khỏi cookie/localStorage. |
| 3 | Hệ thống | Redirect về A-01 (Đăng nhập Admin). |

**Luồng phụ / Ngoại lệ (Alternative/Exception Flow):**

| Mã | Điều kiện | Xử lý |
|----|-----------|-------|
| 38a | Lỗi API logout | Vẫn xóa token cục bộ, redirect về trang đăng nhập. |

**Điều kiện kết thúc (Post-condition):**
- Phiên đăng nhập admin bị xóa.
- Truy cập bất kỳ trang admin nào đều redirect về Đăng nhập.

---

## 4. Mối quan hệ Include / Extend giữa các Use Case

### 4.1. Quan hệ Include (bắt buộc — UC cha luôn gọi UC con)

| UC cha | Include → UC con | Mô tả |
|--------|-------------------|-------|
| UC-08 (Xem video bài giảng) | **include →** UC-09 (Phụ đề đồng bộ) | Khi xem video, hệ thống luôn tải và hiển thị phụ đề đồng bộ (mặc định bật). Phụ đề là thành phần bắt buộc của trải nghiệm xem video. |
| UC-08 (Xem video bài giảng) | **include →** UC-12 (Chia chương bài học) | Khi xem video, hệ thống luôn tải danh sách chương và hiển thị markers trên seekbar. Chia chương là phần tích hợp sẵn trong player. |
| UC-08 (Xem video bài giảng) | **include →** UC-16 (Theo dõi tiến độ) | Khi xem video, hệ thống tự động tracking và cập nhật tiến độ (vị trí video, % hoàn thành) mà không cần học viên thao tác. |
| UC-07 (Thanh toán khóa học) | **include →** UC-06 (Xem chi tiết khóa học) | Trước khi thanh toán, học viên bắt buộc phải xem chi tiết khóa học (nơi chứa nút "Mua khóa học"). |
| UC-27 (Upload video) | **include →** UC-28 (Pipeline STT → Vector) | Sau khi upload thành công, pipeline xử lý tự động được trigger bắt buộc (không cần Admin kích hoạt thủ công). |
| UC-28 (Pipeline STT → Vector) | **include →** UC-29 (Duyệt Transcript) | Sau khi STT hoàn tất, transcript luôn sẵn sàng cho Admin duyệt/chỉnh sửa. Đây là bước kiểm duyệt bắt buộc trong quy trình. |

### 4.2. Quan hệ Extend (tùy chọn — UC con mở rộng UC cha khi có điều kiện)

| UC cha | Extend ← UC con | Điều kiện kích hoạt | Mô tả |
|--------|-------------------|---------------------|-------|
| UC-08 (Xem video bài giảng) | **extend ←** UC-10 (Đặt câu hỏi AI) | Học viên chủ động nhấn nút "Hỏi AI" trong khi xem video. | Chức năng AI Q&A là tùy chọn, chỉ kích hoạt khi học viên muốn hỏi. |
| UC-08 (Xem video bài giảng) | **extend ←** UC-11 (Tóm tắt bài giảng AI) | Học viên chủ động nhấn nút "Tóm tắt" trong khi xem video. | Chức năng tóm tắt AI là tùy chọn, chỉ kích hoạt khi học viên yêu cầu. |
| UC-08 (Xem video bài giảng) | **extend ←** UC-13 (Ghi chú theo mốc thời gian) | Học viên chủ động nhấn nút "Ghi chú" tại một thời điểm trong video. | Ghi chú là tùy chọn, chỉ kích hoạt khi học viên muốn ghi lại nội dung. |
| UC-08 (Xem video bài giảng) | **extend ←** UC-14 (Quiz giữa video) | Video phát đến mốc thời gian có quiz được Admin cài đặt. | Quiz xuất hiện tự động theo điều kiện mốc thời gian, nhưng chỉ khi Admin đã gán quiz (không phải mọi video đều có). |
| UC-02 (Đăng nhập) | **extend ←** UC-03 (Quên mật khẩu) | Học viên không nhớ mật khẩu, chọn "Quên mật khẩu?". | Đặt lại mật khẩu là luồng mở rộng từ đăng nhập, chỉ khi cần. |
| UC-06 (Xem chi tiết khóa học) | **extend ←** UC-07 (Thanh toán khóa học) | Học viên chưa mua khóa và nhấn "Mua khóa học". | Thanh toán chỉ xảy ra nếu khóa chưa được mua và không miễn phí. |
| UC-15 (Làm bài tập) | **extend ←** UC-08 (Xem video bài giảng) | Sau khi xem xong video, học viên chọn làm bài tập liên quan. | Bài tập cuối bài mở rộng từ hoạt động xem bài giảng. |
| UC-25 (Quản lý khóa học) | **extend ←** UC-26 (Quản lý cấu trúc bài giảng) | Admin tạo xong khóa học và muốn thêm nội dung bài giảng. | Cấu trúc bài giảng mở rộng từ quản lý khóa học. |
| UC-30 (Quản lý ngân hàng đề thi) | **extend ←** UC-31 (Quản lý bài tập) | Admin tạo xong bộ đề và muốn gán vào bài giảng. | Gán bài tập mở rộng từ quản lý đề thi. |

### 4.3. Sơ đồ tổng hợp quan hệ (dạng text — để vẽ diagram)

```
──────────────────────────────────────────────────────
                    HỌC VIÊN (Mobile App)
──────────────────────────────────────────────────────

UC-01 Đăng ký ──────────────────────────────────┐
UC-02 Đăng nhập ─── extend ← UC-03 Quên MK      │ Xác thực
UC-20 Đăng xuất ─────────────────────────────────┘

UC-05 Duyệt khóa học ──→ UC-06 Xem chi tiết ─── extend ← UC-07 Thanh toán
                                                              │
                                                    include ↓
                                              (Xem chi tiết khóa)

UC-08 Xem video bài giảng (TRUNG TÂM)
  ├── include → UC-09  Phụ đề đồng bộ
  ├── include → UC-12  Chia chương bài học
  ├── include → UC-16  Theo dõi tiến độ
  ├── extend  ← UC-10  AI Trợ giảng Q&A (RAG)
  ├── extend  ← UC-11  Tóm tắt bài giảng AI
  ├── extend  ← UC-13  Ghi chú mốc thời gian
  ├── extend  ← UC-14  Quiz giữa video
  └── extend  ← UC-15  Bài tập cuối bài

UC-17 Khóa học đã mua / Thư viện
UC-18 Lịch sử thanh toán

──────────────────────────────────────────────────────
                QUẢN TRỊ VIÊN (Web Admin)
──────────────────────────────────────────────────────

UC-23 Đăng nhập Admin
UC-38 Đăng xuất Admin

UC-24 Dashboard tổng quan

UC-25 Quản lý khóa học ─── extend ← UC-26 Cấu trúc bài giảng
                                         │
                                   extend ← UC-27 Upload video
                                              │
                                        include → UC-28 Pipeline (STT → Vector)
                                                    │
                                              include → UC-29 Duyệt Transcript

UC-30 Ngân hàng đề thi ─── extend ← UC-31 Quản lý bài tập

UC-32 Quản lý học viên
UC-33 Quản lý doanh thu
UC-34 Báo cáo phân tích hành vi
UC-35 Thống kê câu hỏi AI
UC-36 Quản lý danh mục
UC-37 Cài đặt hệ thống
```

---

## 5. Tổng hợp thống kê

| Hạng mục | Số lượng |
|----------|----------|
| Tổng Actor | **2** (Học viên, Quản trị viên) |
| Tổng Use Case | **38** |
| UC Học viên (Mobile) | 22 |
| UC Quản trị viên (Web Admin) | 16 |
| UC có đặc tả chi tiết | **26** (toàn bộ UC ưu tiên Cao) |
| Quan hệ Include | **6** |
| Quan hệ Extend | **9** |

---

> **Ghi chú:** Tài liệu này là cơ sở để vẽ Use Case Diagram (UML) và phát triển chi tiết ở các giai đoạn tiếp theo (Sequence Diagram, Class Diagram, API Specification).
