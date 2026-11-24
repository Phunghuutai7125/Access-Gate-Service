# Hướng dẫn chạy cục bộ — Access Gate Service

Tài liệu hướng dẫn triển khai và kiểm thử Access Gate Service trên máy cục bộ hoặc máy chấm bài của Giảng viên.

---

## Cách 1: Chạy bằng Docker Compose (Khuyến nghị ⭐)

Yêu cầu máy đã cài đặt Docker và Docker Compose.

### Bước 1: Sao chép file cấu hình môi trường
```bash
cp .env.example .env
```

### Bước 2: Khởi động hệ thống (PostgreSQL + API Service)
```bash
docker compose up --build -d
```

### Bước 3: Kiểm tra trạng thái hoạt động
```bash
# Kiểm tra log khởi động
docker compose logs -f api

# Kiểm tra endpoint Health
curl http://localhost:8000/health
```

### Bước 4: Mở giao diện Web Dashboard
Mở trình duyệt truy cập:
👉 **http://localhost:8000/** (Giao diện Barrier trực quan)
👉 **http://localhost:8000/docs** (Swagger OpenAPI UI)

---

## Cách 2: Chạy trực tiếp với Python venv (Development)

Yêu cầu máy có Python 3.11 hoặc 3.12 và một PostgreSQL server đang chạy.

### Bước 1: Tạo và kích hoạt môi trường ảo
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Bước 2: Cài đặt thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### Bước 3: Cấu hình biến môi trường
Thiết lập các biến môi trường kết nối database trong file `.env` hoặc export:
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=access_gate_db
export DB_USER=access_gate_user
export DB_PASSWORD=changeme
export CORE_BUSINESS_URL=http://192.168.1.61:8001
export ACCESS_GATE_API_TOKEN=dev-secret-token
```

### Bước 4: Khởi chạy Uvicorn Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Kiểm thử nhanh bằng lệnh cURL

### 1. Quẹt thẻ thành công (Gọi Core Business)
```bash
curl -X POST http://localhost:8000/access/swipe \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-secret-token" \
  -d '{
    "cardId": "RFID-2026-001",
    "gateId": "GATE-01",
    "direction": "IN"
  }'
```

### 2. Xem lịch sử quẹt thẻ gần nhất
```bash
curl -X GET "http://localhost:8000/access/logs/recent?limit=10" \
  -H "Authorization: Bearer dev-secret-token"
```

### 3. Tra cứu trạng thái cổng Barrier
```bash
curl -X GET http://localhost:8000/gates/GATE-01/status \
  -H "Authorization: Bearer dev-secret-token"
```
