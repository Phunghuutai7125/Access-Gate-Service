# Demo Pack — Access Gate Service (team-gate)

Chuẩn bị theo `DemoPack.md` (FIT4110_Student_Kit / 05_Assessment) — Plug-a-thon.

---

## 1. Bài toán và boundary

**Access Gate Service** mô phỏng hệ thống kiểm soát ra/vào bằng thẻ RFID/QR tại các cổng của campus, là 1 trong 7 service của Smart Campus Operations Platform.

```
┌──────────────┐  UID quẹt thẻ    ┌──────────────┐   POST /access/check   ┌────────────────┐
│ Pi RFID       │ ───MQTT────────▶ │ mqtt_listener │                        │  Core Business  │
│ Simulator     │  (HiveMQ Cloud)  │  (team-gate)   │                        │  (policy engine)│
│ (giảng viên)  │                  └──────┬─────────┘                        └────────────────┘
└──────────────┘                          │ ghi                                     ▲
                                            ▼                                        │
                                  ┌──────────────────┐   GET /cards, /gates,          │
                                  │  PostgreSQL (db)   │◀──/access/logs ──────────────┘
                                  └──────────────────┘        (REST API - Access Gate API)
                                            ▲
                                            │ publish
                                            ▼
                                  ┌──────────────────┐
                                  │  HiveMQ topic:     │──▶ Analytics team (subscribe)
                                  │ events/access       │
                                  └──────────────────┘
```

**Boundary:** team-gate chịu trách nhiệm nhận UID thật từ thiết bị RFID (qua HiveMQ), đối chiếu whitelist, lưu nhật ký ra/vào, và cung cấp API tra cứu. Quyết định policy cho phép/từ chối chi tiết theo chính sách nghiệp vụ thuộc về Core Business, không phải Access Gate.

---

## 2. Contract

- **OpenAPI version:** `team-gate.openapi.yaml` — OpenAPI 3.1.0 (chốt từ Lab02, không đổi qua Lab03–06)
- **Event contract (MQTT):** input topic `smart-campus/raw/access/rfid-uid`, output topic `smart-campus/events/access` — payload theo tài liệu AccessGate của giảng viên (mục 4, 7)
- **Endpoint chính (team-gate là Provider — Pair-03):**
  - `GET /health`
  - `GET /cards/{cardId}`, `POST /cards`
  - `GET /gates/{gateId}/status`
  - `GET /access/logs/recent`, `GET /access/logs/{logId}`
- **Endpoint team-gate gọi ra ngoài (team-gate là Consumer — Pair-10, gọi Core Business):**
  - `POST /access/check`, `GET /policies/access/{policyId}`, `GET /health`
- **Quan hệ provider/consumer:**
  | Pair | team-gate là | Đối tác | Cơ chế |
  |---|---|---|---|
  | Pair-03 | Provider | Core Business | REST (LAN lớp, IP tĩnh) |
  | Pair-09 | Producer | Analytics | MQTT (HiveMQ Cloud, không qua LAN) |
  | Pair-10 | Consumer | Core Business | REST — **chưa implement code gọi thật (xem mục 6)** |

---

## 3. Chạy (clone sạch)

```powershell
git clone https://github.com/Phunghuutai7125/Access-Gate-Service.git
cd Access-Gate-Service/lap5
copy .env.example .env
cd ../lap6
copy .env.example .env
# dien MQTT_PASSWORD that vao lap6/.env (khong commit)
cd ../lap5
npm run install:cli
docker compose up -d --build
```

**Cấu hình cần thiết** (`.env.example` ở cả `lap5` và `lap6` — không chứa secret thật):
```
# lap5/.env.example
APP_PORT=8000
POSTGRES_USER=access_gate_user
POSTGRES_PASSWORD=<đổi giá trị thật khi deploy>
POSTGRES_DB=access_gate_db
ACCESS_GATE_API_TOKEN=<đổi giá trị thật khi deploy>

# lap6/.env.example
MQTT_HOST=f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=DVKN2026
MQTT_PASSWORD=<dien-password-that-khong-commit>
```

---

## 4. Kiểm chứng

| Loại | Lệnh | Kết quả mong đợi |
|---|---|---|
| Health | `curl http://192.168.1.31:8000/health` | `200 {"status":"ok",...}` |
| Happy-path (REST) | `GET /access/logs/recent?limit=5` (kèm Bearer token) | `200`, trả UID thật dạng `04:A1:B2:C3:D4:0X` |
| Lỗi dự kiến | `GET /cards/RFID-0000-000` | `404`, ProblemDetails đầy đủ |
| Happy-path (MQTT) | Subscribe `smart-campus/events/access` trên HiveMQ | Nhận event `access_result: granted/denied` mỗi ~10-60s |
| Test report | `lap5/reports/newman-lab05-compose.xml` / `.html` | 40/40 assertions pass |

---

## 5. Tích hợp

**Dependency topology (4 container, Docker Compose):**
```
db (Postgres, healthcheck pg_isready)
  ├─▶ gate-worker (healthcheck /health)
  ├─▶ mqtt-listener (subscribe HiveMQ, ghi access_logs)
  └─▶ api (depends_on: db healthy, gate-worker healthy)
```
Network nội bộ: `team-internal` (đã verify: `api` gọi `gate-worker` qua tên container).

**Contract version dùng cho handshake:** `team-gate.openapi.yaml` (OpenAPI 3.1.0, chốt Lab02).

**Kết quả handshake:**

| Pair | Đối tác | Trạng thái | Bằng chứng |
|---|---|---|---|
| Pair-03 (Core Business gọi team-gate) | Core Business | ✅ Đã gửi IP tĩnh `192.168.1.31:8000` + token qua chat, chờ Core Business xác nhận kết quả gọi thử | `lap5/evidence/` |
| Pair-09 (team-gate → Analytics, MQTT) | Analytics | ✅ Đã publish thật lên `smart-campus/events/access`, đã gửi thông tin broker/topic cho Analytics | `lap6/evidence/06-e2e-mqtt-to-restapi-real-data.png` |
| Pair-10 (team-gate gọi Core Business) | Core Business | ⬜ Chưa thực hiện — chưa có URL/token của Core Business, chưa viết code gọi `POST /access/check` | — |

**Xác nhận end-to-end thật (MQTT → DB → REST API):**
```
Pi RFID Simulator (giảng viên) → HiveMQ (smart-campus/raw/access/rfid-uid)
  → mqtt_listener (team-gate, Docker) → Postgres (access_logs)
  → GET /access/logs/recent → trả UID thật (vd 04:A1:B2:C3:D4:08, granted, uid_matched)
```
Đã verify bằng `psql SELECT` trực tiếp và `curl GET /access/logs/recent` cho cùng kết quả khớp nhau.

---

## 6. Minh chứng và giới hạn

**Đường dẫn report/ảnh chụp:**
- `lap4/reports/newman-lab04-local.xml` / `.html` — 40/40 pass (container đơn lẻ)
- `lap4/evidence/` — build, run, health, newman, teammate pull-run (5 ảnh)
- `lap5/reports/newman-lab05-compose.xml` / `.html` — 40/40 pass (Docker Compose)
- `lap5/evidence/` — compose up, readiness checks, DB thật, network nội bộ, newman pass (5 ảnh)
- `lap5/checklists/readiness-checklist.md` — 6/6 mục đã tick
- `lap6/evidence/` — kết nối HiveMQ thật, granted/denied, end-to-end MQTT→DB→REST

**Known issues (trung thực):**
1. **Pair-10 (team-gate gọi Core Business) chưa implement** — mới dừng ở phân tích hợp đồng Lab02 (3 endpoint cần gọi: `POST /access/check`, `GET /policies/access/{policyId}`, `GET /health`). Chưa có URL/token thật của Core Business tại thời điểm viết bản cập nhật này.
2. **Pair-03 chưa có xác nhận ngược từ Core Business** — đã gửi IP tĩnh + token, chưa nhận phản hồi kết quả test của họ.
3. **`gate-worker`** (mô phỏng nội bộ, khác với `mqtt-listener`) chỉ lưu event trong RAM, mất khi container restart — chấp nhận được vì chỉ là service demo nội bộ cho Lab05, không phải đường dẫn Pair-09 thật (Pair-09 thật đã chuyển sang dùng `mqtt-listener` + HiveMQ + Postgres, ổn định hơn).
4. **IP tĩnh `192.168.1.31`** do giảng viên gán theo MAC address cho mạng lớp — chỉ hoạt động trong mạng LAN lớp học lúc có mặt, không phải địa chỉ public.
5. Câu hỏi mở với Core Business (từ Lab02, chưa chốt): timeout tối đa `/access/check`, chính sách fail-open/fail-closed, `reasonCode` có enum cố định hay không.

---

## 7. Đóng góp

Xem `CONTRIBUTION.md` tại root repo khi có công việc chung với nhóm khác (chưa tạo tại thời điểm viết bản cập nhật này — cần bổ sung nếu Plug-a-thon yêu cầu ghi nhận đóng góp chéo nhóm).

---

*Cập nhật lần 2 — sau khi hoàn thành handshake IP tĩnh với Core Business và nối mqtt_listener vào Postgres. Dùng commit thông thường để ghi nhận thay đổi (không amend/force-push).*