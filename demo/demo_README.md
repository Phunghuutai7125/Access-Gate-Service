# Demo Pack — Access Gate Service (team-gate)

Chuẩn bị theo `DemoPack.md` (FIT4110_Student_Kit / 05_Assessment) — Plug-a-thon.

---

## 1. Bài toán và boundary

**Access Gate Service** mô phỏng hệ thống kiểm soát ra/vào bằng thẻ RFID/QR tại các cổng của campus, là 1 trong 7 service của Smart Campus Operations Platform.

```
┌──────────────┐  RFID quẹt thẻ   ┌──────────────────┐  POST /access/check   ┌────────────────┐
│  RFID Reader │ ───────────────▶ │  Access Gate API  │ ─────────────────────▶ │  Core Business  │
│  (thiết bị)  │                  │  (team-gate)       │ ◀───────────────────── │  (policy engine)│
└──────────────┘                  └──────┬─────────────┘  allow/deny + reason  └────────────────┘
                                          │
                                          │ async event (POST /events/access)
                                          ▼
                                  ┌──────────────────┐
                                  │   Analytics       │ (mô phỏng bởi gate-worker trong nội bộ)
                                  └──────────────────┘
                                          │
                                          ▼
                                  ┌──────────────────┐
                                  │  PostgreSQL (db)   │ ← lưu cards, gates, access_logs
                                  └──────────────────┘
```

**Boundary:** team-gate chịu trách nhiệm quản lý thẻ (`cards`), trạng thái cổng (`gates`) và nhật ký ra/vào (`access_logs`). Quyết định cho phép/từ chối (policy) thuộc về Core Business, không phải Access Gate.

---

## 2. Contract

- **OpenAPI version:** `team-gate.openapi.yaml` — OpenAPI 3.1.0 (chốt từ Lab02, không đổi qua Lab03–05)
- **Endpoint chính (team-gate là Provider — Pair-03):**
  - `GET /health`
  - `GET /cards/{cardId}`, `POST /cards`
  - `GET /gates/{gateId}/status`
  - `GET /access/logs/recent`, `GET /access/logs/{logId}`
- **Endpoint team-gate gọi ra ngoài (team-gate là Consumer — Pair-10, gọi Core Business):**
  - `POST /access/check` — gửi `cardId, gateId, direction, timestamp, personId`
  - `GET /policies/access/{policyId}`
  - `GET /health`
- **Quan hệ provider/consumer:**
  | Pair | team-gate là | Đối tác |
  |---|---|---|
  | Pair-03 | Provider | Core Business |
  | Pair-09 | Consumer (async event) | Analytics (mô phỏng bởi `gate-worker`) |
  | Pair-10 | Consumer | Core Business |

---

## 3. Chạy (clone sạch)

```powershell
git clone https://github.com/Phunghuutai7125/Access-Gate-Service.git
cd Access-Gate-Service/lap5
copy .env.example .env
npm run install:cli
docker compose up -d --build
```

**Cấu hình cần thiết** (`.env.example` — không chứa secret thật):
```
APP_PORT=8000
POSTGRES_USER=access_gate_user
POSTGRES_PASSWORD=<đổi giá trị thật khi deploy>
POSTGRES_DB=access_gate_db
ACCESS_GATE_API_TOKEN=<đổi giá trị thật khi deploy>
GATE_WORKER_URL=http://gate-worker:9000
```

---

## 4. Kiểm chứng

| Loại | Lệnh | Kết quả mong đợi |
|---|---|---|
| Health | `curl http://localhost:8000/health` | `200 {"status":"ok",...}` |
| Happy-path | `GET /cards/RFID-9215-649` (kèm Bearer token) | `200`, trả đúng Card schema |
| Lỗi dự kiến | `GET /cards/RFID-0000-000` (kèm Bearer token) | `404`, ProblemDetails (`type`, `title`, `status`, `detail`, `instance`) |
| Test report | `reports/newman-lab05-compose.xml` và `.html` | 40/40 assertions pass |

---

## 5. Tích hợp

**Dependency topology:**
```
db (Postgres, healthcheck pg_isready)
  └─▶ gate-worker (healthcheck /health)
        └─▶ api (depends_on: db healthy, gate-worker healthy)
```
Network nội bộ: `team-internal` (đã verify: `api` gọi `gate-worker` qua tên container, không qua `localhost`).

**Contract version dùng cho handshake:** `team-gate.openapi.yaml` (OpenAPI 3.1.0, chốt Lab02).

**Kết quả handshake với Core Business (Pair-03/10):** _(điền sau khi test chéo thật với nhóm Core Business — xem mục 6 known issues)_

---

## 6. Minh chứng và giới hạn

**Đường dẫn report/ảnh chụp:**
- `lap4/reports/newman-lab04-local.xml` / `.html` — 40/40 pass (container đơn lẻ)
- `lap4/evidence/` — 5 ảnh (build, run, health, newman, teammate pull-run)
- `lap5/reports/newman-lab05-compose.xml` / `.html` — 40/40 pass (Docker Compose 3 container)
- `lap5/evidence/` — 5 ảnh (compose up, readiness checks, DB thật, network nội bộ, newman pass)
- `lap5/checklists/readiness-checklist.md` — 6/6 mục đã tick

**Known issues (trung thực):**
1. **Chưa test handshake thật với nhóm Core Business** — chưa có URL/token thật từ họ tại thời điểm viết demo pack này. Code `POST /access/check` gọi Core Business **chưa được implement** trong `main.py` (team-gate hiện chỉ đóng vai Provider đã verify, vai Consumer mới dừng ở phân tích hợp đồng Lab02).
2. **gate-worker chỉ lưu event trong RAM**, chưa ghi vào Postgres — mất dữ liệu khi container restart. Chấp nhận được vì gate-worker chỉ đóng vai trò mô phỏng Analytics tối thiểu theo đề bài Lab05.
3. **Câu hỏi mở với Core Business** (từ Lab02, chưa chốt): timeout tối đa `/access/check`, chính sách fail-open/fail-closed khi Core Business lỗi, `reasonCode` có enum cố định hay không.
4. Image push GHCR dùng tag cố định `v0.1.0-team-gate-lab05` — chưa có versioning tự động theo commit.

---

## 7. Đóng góp

Xem `CONTRIBUTION.md` tại root repo khi có công việc chung với nhóm khác (chưa tạo tại thời điểm viết demo pack này — cần bổ sung nếu Plug-a-thon yêu cầu ghi nhận đóng góp chéo nhóm).

---

*Dùng commit thông thường để ghi nhận thay đổi vào demo pack này khi có cập nhật (không amend/force-push).*
