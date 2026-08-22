# RUN_LOCAL.md — Access Gate Service (Lab04)

Hướng dẫn chạy lại service trong Docker container và kiểm thử bằng Newman.

## Yêu cầu môi trường
- Docker Desktop đang chạy (`docker info` phải trả về Server info, không lỗi)
- Node.js 20.x + npm

## Các bước

### 1. Cài dependency (Prism / Spectral / Newman)
```
npm run install:cli
```

### 2. Build Docker image
```
docker build -t fit4110/access-gate:lab04 .
```

### 3. Chạy container
```
docker run --rm --name fit4110-gate-lab04 -p 8000:8000 --env-file .env.example fit4110/access-gate:lab04
```

### 4. Kiểm tra health (mở terminal khác)
```
curl http://localhost:8000/health
```
Kỳ vọng: `{"status":"ok","service":"access-gate-service", ...}`

### 5. Chạy lại Postman/Newman test trên container
```
npm run test:local
```
Report xuất ra tại:
- `reports/newman-lab04-local.xml`
- `reports/newman-lab04-local.html`

## Dừng container
```
docker stop fit4110-gate-lab04
```

## Ghi chú
- Service dùng in-memory data (không cần DB thật để chạy Lab04), nhưng `.env.example` đã khai báo sẵn biến `DB_*` theo yêu cầu đề bài — khi nối DB thật, đọc các biến này trong `main.py`.
- Token test mặc định: `dev-secret-token` (khai trong `.env.example`, khớp với `postman/environments/lab04_local.postman_environment.json`). Đổi cả hai nơi nếu muốn dùng token khác.
- Image chạy bằng user non-root (`appuser`), có `HEALTHCHECK` gọi `GET /health` mỗi 15s.
