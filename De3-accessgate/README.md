# Smart Campus — Access Gate Service (Đề tài 3)

Học phần: **Dịch vụ kết nối và Công nghệ nền tảng (FIT4110)**  
Đơn vị: **Khoa Công nghệ thông tin — Trường Đại học Đại Nam**  
Nhóm thực hiện: **AccessGate** (Product A / Product B)

---

## 📌 Giới thiệu dự án

Trong kiến trúc tổng thể của **Smart Campus Operations Platform**, **Access Gate Service** đóng vai trò là chốt chặn an ninh vật lý kiểm soát toàn bộ luồng người ra/vào khuôn viên trường thông qua hệ thống Barrier thông minh và đầu đọc thẻ RFID.

### Điểm nổi bật về kiến trúc & tích hợp:
1. **Ranh giới dịch vụ chuẩn mực (Service Boundary)**: Nắm giữ dữ liệu chủ quyền về thẻ (`cards`), cổng Barrier (`gates`), và nhật ký ra vào (`access_logs`).
2. **Hợp đồng API chuẩn OpenAPI 3.1.0**: Có đầy đủ JSON Schema, validation regex, mã lỗi chuẩn **RFC 7807 Problem Details** (`application/problem+json`).
3. **Kết nối đồng bộ thời gian thực (Cặp #10 & #3 với Core Business)**:
   - Giao tiếp với Core Business qua `POST /access/check` với SLA cam kết ≤ 200ms.
   - Cơ chế an ninh tối cao **Fail-closed**: Tự động từ chối (`DENY`) khi Core Business gặp sự cố hoặc timeout > 1.5s.
4. **Kết nối bất đồng bộ (Cặp #09 với Analytics Service)**: Tự động publish event `access.log.created` và `access.denied` sang broker MQTT của Analytics để phục vụ phân tích số liệu và live dashboard.
5. **Giao diện Web trực quan (UI Simulator)**: Tích hợp sẵn tại `GET /` mô phỏng trực quan đóng/mở Barrier, hiển thị đèn tín hiệu và nhật ký theo thời gian thực.
6. **Đóng gói công nghệ nền tảng**: Đầy đủ Dockerfile, docker-compose.yml và cơ chế database healthcheck retry on startup.

---

## 📂 Cấu trúc thư mục

```
De3-accessgate/
├── main.py                  # Mã nguồn FastAPI hoàn chỉnh (API + Core Client + UI)
├── requirements.txt         # Danh mục thư viện Python
├── Dockerfile               # Đóng gói Docker image
├── docker-compose.yml       # Điều phối PostgreSQL và API service
├── .dockerignore            # Loại bỏ file rác khi build Docker
├── .env.example             # Mẫu biến môi trường
├── openapi.yaml             # Hợp đồng API chuẩn OpenAPI 3.1.0
├── service_boundary.md      # Tài liệu phân tích ranh giới dịch vụ & sơ đồ
├── endpoint_catalog.md      # Danh mục chi tiết các endpoint
├── RUN_LOCAL.md             # Hướng dẫn chạy nhanh trên máy cục bộ
├── static/
│   └── index.html           # Giao diện Web trực quan Barrier & Dashboard
└── postman/                 # Bộ kiểm thử tích hợp tự động
```

---

## 🚀 Khởi động nhanh bằng Docker

```bash
# 1. Khởi chạy toàn bộ hệ thống
docker compose up --build -d

# 2. Truy cập hệ thống
Giao diện trực quan: http://localhost:8000/
Tài liệu Swagger:     http://localhost:8000/docs
Kiểm tra Health:     http://localhost:8000/health
```

Chi tiết các cách chạy khác xem tại [RUN_LOCAL.md](RUN_LOCAL.md).
