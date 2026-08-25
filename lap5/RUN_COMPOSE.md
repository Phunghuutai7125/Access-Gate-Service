# RUN_COMPOSE.md — Access Gate Service Stack (Lab05)

Hướng dẫn chạy lại toàn bộ stack (API + DB + gate-worker) bằng Docker Compose.

## Yêu cầu môi trường
- Docker Desktop đang chạy, hỗ trợ Compose v2 (`docker compose version` phải chạy được)
- Node.js 20.x + npm (để chạy Newman)

## Các bước

### 1. Copy cấu hình môi trường
```powershell
copy .env.example .env
```
(sửa giá trị thật trong `.env` nếu cần, không commit file `.env`)

### 2. Cài dependency Newman
```powershell
npm run install:cli
```

### 3. Build & chạy toàn bộ stack
```powershell
docker compose up -d --build
```
Compose sẽ khởi động theo thứ tự: `db` (chờ pg_isready) → `gate-worker` (chờ /health) → `api`.

### 4. Theo dõi log
```powershell
docker compose logs -f
```

### 5. Kiểm tra readiness từng service
```powershell
docker exec -it fit4110-db-lab05 pg_isready -U access_gate_user
curl.exe http://localhost:9000/health
curl.exe http://localhost:8000/health
```

### 6. Chạy lại Postman/Newman test trên stack
```powershell
npm run test:local
```
Report xuất ra `reports/newman-lab05-compose.xml` và `.html`.

## Dừng toàn bộ stack
```powershell
docker compose down
```
(thêm `-v` nếu muốn xoá luôn volume DB: `docker compose down -v`)

## Ghi chú
- `api` gọi `gate-worker` qua tên container `gate-worker` (không phải `localhost`) — đúng cơ chế network nội bộ `team-internal` của Docker Compose.
- team-gate không dùng AI service theo phân công đề bài — `gate-worker` đóng vai trò nhận async event (pair-09 gửi sang Analytics), thay cho AI/YOLO của các nhóm khác.
