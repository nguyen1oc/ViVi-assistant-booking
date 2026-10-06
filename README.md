# Hệ thống Đặt lịch Lái thử xe VinFast + Trợ lý ViVi (P-053)

[![Backend CI](https://github.com/nguyen1oc/ViVi-assistant-booking/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/nguyen1oc/ViVi-assistant-booking/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/nguyen1oc/ViVi-assistant-booking/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/nguyen1oc/ViVi-assistant-booking/actions/workflows/frontend-ci.yml)

Nhóm em xây dựng dự án này nhằm mang đến giải pháp toàn diện giúp khách hàng dễ dàng tìm hiểu thông tin và đăng ký lái thử các dòng xe ô tô điện VinFast. Người dùng có thể xem danh mục xe, tương tác trực tiếp với trợ lý trí tuệ nhân tạo ViVi để tìm kiếm showroom phù hợp và thực hiện các thao tác tạo mới, tra cứu, dời lịch hoặc hủy lịch lái thử thông qua mã xác thực OTP.

Bên cạnh giao diện dành cho khách hàng, nhóm em còn cung cấp Cổng thông tin nội bộ (Internal Portal) dành cho đội ngũ vận hành và bộ hồ sơ khách hàng hỗ trợ nhân viên tư vấn sau buổi lái thử.

---

##  Mục lục

1. [Các thành phần chính của ứng dụng](#1-các-thành-phần-chính-của-ứng-dụng)
2. [Môi trường triển khai tham khảo](#2-môi-trường-triển-khai-tham-khảo)
3. [Công nghệ nhóm em sử dụng](#3-công-nghệ-nhóm-em-sử-dụng)
4. [Cấu trúc thư mục dự án](#4-cấu-trúc-thư-mục-dự-án)
5. [Tài liệu dự án](#5-tài-liệu-dự-án)
6. [Hướng dẫn chạy dự án trên máy cá nhân (Local)](#6-hướng-dẫn-chạy-dự-án-trên-máy-cá-nhân-local)
7. [Tài khoản Cổng nội bộ](#7-tài-khoản-cổng-nội-bộ)
8. [Hướng dẫn thử nghiệm luồng Tra cứu - Đổi - Hủy lịch](#8-hướng-dẫn-thử-nghiệm-luồng-tra-cứu---đổi---hủy-lịch)
9. [An toàn và bảo mật dữ liệu](#9-an-toàn-và-bảo-mật-dữ-liệu)
10. [Continuous Integration](#10-continuous-integration)
11. [Video Demo](#11-video-demo)
12. [Pitch Deck](#12-pitch-deck)

---

## 1. Các thành phần chính của ứng dụng

Hệ thống được nhóm em thiết kế gồm các thành phần phục vụ từng nhóm đối tượng người dùng:

- **Trang web dành cho khách hàng (`frontend`)**: Giao diện chính giúp người dùng xem thông số xe, tương tác với trợ lý ảo ViVi và đăng ký lịch lái thử.
- **Cổng thông tin nội bộ (`internal-portal/frontend`)**: Giao diện riêng dành cho Nhân viên (Staff), Quản lý Showroom và Quản trị viên (Operations Admin) để tiếp nhận, điều phối và xử lý lịch hẹn.
- **Hệ thống xử lý trung tâm (`backend`)**: Được xây dựng bằng Python FastAPI kết hợp bộ trí tuệ nhân tạo LangGraph để xử lý nghiệp vụ đặt chỗ, hội thoại AI, xác thực OTP và lưu trữ dữ liệu. Module `backend/src/internal_portal` xử lý riêng phần xác thực và phân quyền cho Cổng nội bộ.

---

## 2. Môi trường triển khai tham khảo

Repository công khai này không chứa URL hoặc credential của môi trường production. Khi tự triển khai, hãy cấu hình endpoint và secret của riêng bạn qua biến môi trường:

| Thành phần hệ thống | Dịch vụ đám mây | Địa chỉ truy cập thực tế |
| --- | --- | --- |
| Trang web khách hàng | Static hosting (ví dụ Cloudflare Pages) | Cấu hình `VITE_API_BASE_URL` khi build |
| Cổng thông tin nội bộ | Static hosting riêng | Cấu hình `VITE_INTERNAL_API_BASE_URL` khi build và giới hạn truy cập phù hợp |
| Máy chủ xử lý API | Container hosting (ví dụ Google Cloud Run) | Cấu hình `CORS_ORIGINS`, database và các secret tại môi trường deploy |
| Kiểm tra trạng thái máy chủ | FastAPI Health | `GET /health` trên endpoint backend của bạn |
| Cơ sở dữ liệu đám mây | Managed PostgreSQL | Được kết nối bảo mật qua biến môi trường `DATABASE_URL` |
| Bộ nhớ đệm & Hàng đợi (Tùy chọn) | Redis Cloud / External | Tùy chọn bật/tắt qua `REDIS_ENABLED` và `REDIS_URL` |
| Kho lưu trữ hình ảnh & video | Object storage / CDN | Cấu hình `MEDIA_BASE_URL` của bạn |

### Mô hình luồng dữ liệu

Để người đọc dễ theo dõi, nhóm em tổng hợp luồng tương tác của dự án theo sơ đồ sau:

```mermaid
flowchart TD
    User["Khách hàng / Nhân viên"] --> Pages["Trang web & Cổng nội bộ<br/>Cloudflare Pages"]
    Pages -->|"Gọi API dữ liệu"| CloudRun["Máy chủ xử lý trung tâm<br/>Google Cloud Run (FastAPI + LangGraph)"]
    Pages -->|"Lấy hình ảnh & video"| R2["Kho dữ liệu đa phương tiện<br/>Cloudflare R2"]
    CloudRun -->|"Lưu trữ & truy xuất dữ liệu"| PostgreSQL[("Cơ sở dữ liệu chính<br/>Managed PostgreSQL")]
    CloudRun -.-|"Hàng đợi & bộ nhớ đệm (Tùy chọn)"| Redis[("Bộ nhớ tạm<br/>Redis")]
```

---

## 3. Công nghệ nhóm em sử dụng

Nhóm em tổng hợp danh sách các công nghệ chính được áp dụng trong dự án:

| Lớp công nghệ | Công nghệ sử dụng | Vai trò và mục đích |
| --- | --- | --- |
| **Giao diện người dùng (Frontend)** | React 18, Vite 5, React Router 7, GSAP, Three.js, Mapbox GL | Nhóm em dùng để xây dựng giao diện tương tác, hiển thị mô hình xe 3D và bản đồ tìm kiếm showroom. |
| **Máy chủ xử lý (Backend)** | Python 3.11, FastAPI, Uvicorn, Pydantic | Nhóm em dùng để tiếp nhận yêu cầu API, xử lý nghiệp vụ đặt chỗ và dời lịch với thời gian phản hồi nhanh. |
| **Trợ lý trí tuệ nhân tạo (AI ViVi)** | LangGraph, LangChain, OpenAI / OpenRouter, Guardrails | Trợ lý tư vấn xe và đặt lịch lái thử, được nhóm em thiết lập bộ ranh giới bảo vệ (Guardrails) nghiêm ngặt. |
| **Cơ sở dữ liệu & Lưu vết** | PostgreSQL 16, Psycopg 3, LangGraph Checkpointer | Lưu trữ thông tin lịch hẹn, danh mục xe, trạng thái khung giờ và lịch sử hội thoại AI. |
| **Bộ nhớ đệm & Hàng đợi** | Redis (Tùy chọn) | Hỗ trợ lưu tạm bản sao OTP, khung giờ giữ chỗ và hàng đợi cập nhật hồ sơ khách hàng. |
| **Đóng gói & Triển khai (DevOps)** | Docker, GitHub Actions, Wrangler, Google Cloud Run | Tự động hóa quá trình đóng gói ứng dụng, kiểm thử mã nguồn và triển khai lên hạ tầng đám mây. |

---

## 4. Cấu trúc thư mục dự án

```text
P-053/
├── frontend/                 # Mã nguồn trang web công khai dành cho khách hàng
├── internal-portal/
│   └── frontend/             # Mã nguồn cổng thông tin quản lý nội bộ cho nhân viên
├── backend/
│   └── src/                  # Mã nguồn các luồng services/agent/langgraph
├── eval/                     # Dữ liệu mẫu (seed dataset) và báo cáo kiểm thử benchmark
├── docs/                     # Tài liệu thiết kế kiến trúc (ARCHITECTURE), PRD, SPEC và Journal
├── presentation/             # Slide thuyết trình và video demo sản phẩm
├── resources/                # Tài liệu hướng dẫn, nghiên cứu và thiết kế tham khảo
├── change_logs/              # Nhật ký ghi nhận các thay đổi kỹ thuật theo ngày
└── docker-compose.yml        # File cấu hình khởi chạy toàn bộ dự án trên máy cá nhân
```

---

## 5. Tài liệu dự án

Nhóm em đã chuẩn bị đầy đủ bộ tài liệu mô tả chi tiết về hệ thống:

- [Kiến trúc hệ thống (ARCHITECTURE.md)](docs/ARCHITECTURE.md)
- [Yêu cầu sản phẩm (PRD.md)](docs/PRD.md)
- [Đặc tả kỹ thuật (SPEC.md)](docs/SPEC.md)
- [Hồ sơ PO Document](docs/PO%20Document.pdf)
- [Nhật ký công việc tuần (JOURNAL.md)](docs/JOURNAL.md)
- [Nhật ký thay đổi mã nguồn](change_logs/)
- [Đánh giá chất lượng và Benchmark](eval/EVALUATION.md)
- [Tài liệu tham khảo](resources/README.md)
- [Slide thuyết trình Demo Day](<presentation/AI 20k_P-053_DulichHaNoi.pdf>)
- [Video demo sản phẩm](<presentation/AI 20k_P-053_DulichHaNoi.mp4>)

---

## 6. Hướng dẫn chạy dự án trên máy cá nhân (Local)

Nếu bạn muốn trải nghiệm chạy thử ứng dụng trên máy cá nhân, nhóm em đã thiết lập sẵn cấu hình Docker Compose. Trước khi chạy, bạn cần thực hiện hai bước chuẩn bị sau.

### Bước chuẩn bị 1: Tải dữ liệu mẫu từ Google Drive

Nhóm em lưu trữ toàn bộ bộ dữ liệu mẫu (V5.2) trên Google Drive vì dung lượng quá lớn để đưa vào kho mã nguồn. Bộ dữ liệu bao gồm 319 showroom, 900 nhân viên, 1.356 xe demo và 9.369 lịch hẹn.

**Tải dữ liệu tại:** <https://drive.google.com/drive/folders/1GtzWl9bM3I80W26HIf8yfgCh1A6M0OS4>

Sau khi tải về, bạn giải nén và đặt các file CSV vào đúng thư mục trong dự án:

```text
eval/
└── datav2/
    └── data-final-v2/    ← Đặt toàn bộ các file CSV vào đây
        ├── 01_provinces.csv
        ├── 02_districts.csv
        └── ...
```

### Bước chuẩn bị 2: Điền thông tin cấu hình vào file `.env`

Bạn tạo file `.env` từ file mẫu có sẵn:

```powershell
Copy-Item .env.example .env
```

Sau đó mở file `.env` và điền các thông tin còn thiếu. Dưới đây là những biến quan trọng bạn cần chú ý:

**Nhóm AI & Mô hình ngôn ngữ:**

| Biến môi trường | Mặc định | Bạn cần làm gì |
| --- | --- | --- |
| `OPENAI_API_KEY` | *(để trống)* | **Bắt buộc** — Điền khóa API OpenAI của bạn để trợ lý ViVi hoạt động |
| `OPENROUTER_API_KEY` | *(để trống)* | Tùy chọn — Dùng thay thế nếu không dùng OpenAI trực tiếp |
| `MODEL_NAME` | `gpt-5.6-luna` | Mô hình chính của trợ lý ViVi; đổi sang mô hình khác nếu cần tiết kiệm chi phí |
| `CLASSIFIER_MODEL_NAME` | `gpt-4o-mini` | Mô hình phân loại ý định câu hỏi; thường giữ nguyên giá trị mặc định |
| `GUARDRAILS_ENABLED` | `true` | Bật bộ kiểm soát đầu vào/đầu ra an toàn; chỉ tắt khi cần debug nhanh |

**Nhóm Cơ sở dữ liệu & Dữ liệu mẫu:**

| Biến môi trường | Mặc định | Bạn cần làm gì |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://vinfast:vinfast@localhost:5432/vinfast_booking` | Giữ nguyên khi chạy Docker; chỉ đổi nếu dùng PostgreSQL bên ngoài |
| `AUTO_LOAD_EVAL_DATA` | `true` | Giữ `true` để hệ thống tự nạp dữ liệu mẫu lần đầu khởi chạy |
| `EVAL_DATA_DIR` | `eval/datav2/data-final-v2` | Đường dẫn đến thư mục CSV đã tải từ Google Drive |
| `REDIS_ENABLED` | `true` | Redis đã bật sẵn trong Docker Compose; giữ nguyên |

**Nhóm Bảo mật & Thông báo:**

| Biến môi trường | Mặc định | Bạn cần làm gì |
| --- | --- | --- |
| `BOOKING_ACCESS_OTP_SECRET` | *(giá trị mẫu)* | **Thay bắt buộc** khi chạy thật — chuỗi ngẫu nhiên tối thiểu 32 ký tự |
| `CONVERSATION_SIGNING_SECRET` | *(giá trị mẫu)* | **Thay bắt buộc** khi chạy thật — tương tự như biến trên |
| `GMAIL_ENABLED` | `false` | Để `false` khi chạy thử; bật lên nếu muốn nhận email OTP thật |
| `NOTIFICATION_POLL_INTERVAL_SECONDS` | `60` | Giảm xuống `5` khi test local để thông báo gửi ngay |

**Nhóm LangSmith — Theo dõi luồng AI (Tùy chọn):**

| Biến môi trường | Mặc định | Bạn cần làm gì |
| --- | --- | --- |
| `LANGSMITH_TRACING` | `false` | Bật `true` để theo dõi toàn bộ bước xử lý AI trên bảng điều khiển LangSmith |
| `LANGSMITH_API_KEY` | *(để trống)* | Điền khóa API LangSmith nếu bật tính năng theo dõi |
| `LANGSMITH_PROJECT` | `vinfast-test-drive` | Tên project hiển thị trên LangSmith; có thể đổi tùy ý |

### Bước 1: Khởi động hệ thống

Sau khi đã chuẩn bị xong dữ liệu và file `.env`, bạn mở cửa sổ dòng lệnh (Terminal / PowerShell) tại thư mục dự án và chạy:

```powershell
docker compose up --build
```

Ở lần khởi động đầu tiên trên cơ sở dữ liệu rỗng, hệ thống sẽ tự động nạp toàn bộ dữ liệu mẫu từ thư mục `EVAL_DATA_DIR`. Quá trình này chỉ diễn ra một lần; những lần chạy tiếp theo hệ thống sẽ tự bỏ qua nếu đã có dữ liệu.

### Bước 2: Truy cập các địa chỉ ứng dụng

Sau khi khởi động xong, bạn mở trình duyệt và truy cập các cổng sau:

- **Trang web dành cho khách hàng:** <http://localhost:3000>
- **Cổng thông tin nội bộ nhân viên:** <http://localhost:3100>
- **Máy chủ API Backend:** <http://localhost:8001>
- **Trang tra cứu API (Swagger UI):** <http://localhost:8001/docs>

---

## 7. Tài khoản Cổng nội bộ

Repository không công bố tài khoản hoặc mật khẩu mặc định. Tạo tài khoản nội bộ ở môi trường local bằng CLI `backend/scripts/manage_internal_user.py`; với môi trường deploy, hãy tạo credential riêng, dùng secret manager và giới hạn truy cập Cổng nội bộ.

---

## 8. Hướng dẫn thử nghiệm luồng Tra cứu - Đổi - Hủy lịch

Khi chạy thử ở máy cá nhân, nhóm em hỗ trợ tính năng OTP giả lập giúp bạn kiểm tra nhanh luồng nghiệp vụ:

1. **Đặt lịch mới:** Bạn thực hiện đăng ký một lịch hẹn lái thử trên trang web khách hàng.
2. **Tra cứu lịch:** Truy cập vào mục *"Quản lý lịch đặt"* và nhập địa chỉ email đã dùng khi đăng ký.
3. **Nhập mã OTP:** Mã OTP thử nghiệm sẽ hiển thị ngay trên khung hội thoại. Bạn điền mã này để xem danh sách lịch hẹn.
4. **Đổi hoặc Hủy lịch:** Bạn tiến hành đổi sang khung giờ lái thử mới hoặc chọn hủy lịch. Hệ thống sẽ cập nhật trạng thái ngay lập tức trên cơ sở dữ liệu.

---

## 9. An toàn và bảo mật dữ liệu

Nhóm em luôn tuân thủ nghiêm ngặt các tiêu chuẩn bảo mật thông tin:

- **Bảo mật mã khóa:** Không lưu trữ mật khẩu, khóa API (OpenAI/OpenRouter) hay chuỗi kết nối cơ sở dữ liệu thật vào mã nguồn.
- **Bảo vệ dữ liệu riêng tư:** Thông tin cá nhân của khách hàng (email, số điện thoại) được che bớt trước khi hiển thị.
- **Ranh giới an toàn cho AI:** Trợ lý ViVi chỉ tư vấn thông tin xe VinFast và đặt lịch lái thử, tuyệt đối không tự ý thay đổi dữ liệu hệ thống khi chưa qua các bước xác thực OTP.

---

## 10. Continuous Integration

Repository public chỉ chạy kiểm tra source, không tự động deploy và không yêu cầu GitHub Actions secret. Backend CI chạy Ruff, Mypy, Bandit, Pytest, benchmark guardrail và agent evaluation. Frontend CI chỉ build hai ứng dụng bằng endpoint `example.invalid` để kiểm tra bundle.

Khi cần triển khai, tạo workflow riêng trong repository private hoặc dùng protected environment. Không đưa credential cloud, API token, database URL có mật khẩu hoặc API key vào repository public.

## 11. Video Demo
[Xem video demo](<presentation/AI 20k_P-053_DulichHaNoi.mp4>)

## 12. Pitch Deck
[Xem Pitch Deck (PDF)](<presentation/AI 20k_P-053_DulichHaNoi.pdf>)

---

*Dự án được nhóm em thực hiện trong khuôn khổ Chương trình AI20K Build Phase (Cohort 3) — Đề tài P-053.*
