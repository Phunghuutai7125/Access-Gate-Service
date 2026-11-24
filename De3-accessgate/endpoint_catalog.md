# Endpoint Catalog — Access Gate Service

Danh mục đầy đủ các REST API endpoint do **Access Gate Service** cung cấp và tiêu thụ.

---

## 1. Endpoints do Access Gate Service cung cấp (Provider)

| STT | Phương thức | Đường dẫn (Path) | Yêu cầu Auth | Consumer chính | Tóm tắt chức năng |
|---|---|---|---|---|---|
| 1 | `GET` | `/` | Không | Trình duyệt / Demo | Giao diện Web trực quan mô phỏng quẹt thẻ, đóng mở Barrier và xem log real-time |
| 2 | `GET` | `/health` | Không | Prometheus, Gateway, K8s | Kiểm tra trạng thái hoạt động (Healthcheck) của service |
| 3 | `POST` | `/access/swipe` | Có (Bearer) | Barrier Device, UI Simulator | Tiếp nhận sự kiện quẹt thẻ, gọi Core Business kiểm tra, ghi log và điều khiển Barrier |
| 4 | `GET` | `/access/logs/recent` | Có (Bearer) | Core Business, Analytics, Admin | Lấy danh sách nhật ký ra/vào gần nhất, hỗ trợ lọc theo `gateId`, `startTime`, `endTime`, phân trang `limit` |
| 5 | `GET` | `/access/logs/{logId}` | Có (Bearer) | Core Business | Xem chi tiết 1 bản ghi quẹt thẻ theo mã định danh UUID |
| 6 | `GET` | `/gates/{gateId}/status`| Có (Bearer) | Core Business, Dashboard | Xem trạng thái vật lý hiện tại của Barrier (`OPEN` hoặc `CLOSED`) |
| 7 | `GET` | `/cards/{cardId}` | Có (Bearer) | Core Business, SIS | Tra cứu thông tin chủ sở hữu thẻ RFID và tình trạng thẻ (`ACTIVE`/`INACTIVE`) |
| 8 | `POST` | `/cards` | Có (Bearer) | Ban quản lý thẻ / Admin | Đăng ký cấp phát thẻ mới (`STUDENT` hoặc `STAFF`) |

---

## 2. Chi tiết hợp đồng các Endpoint chính

### 2.1. `POST /access/swipe` (Quẹt thẻ Barrier)
- **Mục đích**: Nhận yêu cầu quẹt thẻ, gọi Core Business thẩm định, ra quyết định đóng/mở Barrier.
- **Request Body**:
```json
{
  "cardId": "RFID-2026-001",
  "gateId": "GATE-01",
  "direction": "IN"
}
```
- **Response 200 OK**:
```json
{
  "logId": "3d906e18-c3d6-f4f7-edc7-b1a59761d251",
  "cardId": "RFID-2026-001",
  "gateId": "GATE-01",
  "direction": "IN",
  "accessGranted": true,
  "result": "ALLOW",
  "reasonCode": "VALID_CARD",
  "decisionId": "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002",
  "policyId": "POL-001",
  "decisionSource": "CORE",
  "timestamp": "2026-08-27T15:00:01Z"
}
```

### 2.2. `GET /access/logs/recent` (Truy vấn nhật ký)
- **Query Params**:
  - `gateId`: (Tùy chọn) Mã cổng cần lọc (ví dụ `GATE-01`)
  - `startTime`: (Tùy chọn) Thời điểm bắt đầu định dạng ISO 8601
  - `endTime`: (Tùy chọn) Thời điểm kết thúc định dạng ISO 8601
  - `limit`: (Tùy chọn, mặc định 20, tối đa 100)
- **Response 200 OK**:
```json
{
  "items": [
    {
      "logId": "3d906e18-c3d6-f4f7-edc7-b1a59761d251",
      "cardId": "RFID-2026-001",
      "gateId": "GATE-01",
      "direction": "IN",
      "status": "GRANTED",
      "reasonCode": "VALID_CARD",
      "decisionId": "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002",
      "operatorNote": null,
      "timestamp": "2026-08-27T15:00:01Z"
    }
  ],
  "nextCursor": null,
  "hasMore": false
}
```

---

## 3. Endpoint do Access Gate Service tiêu thụ (Consumer)

### `POST /access/check` (Core Business Service)
- **Địa chỉ gọi**: `POST http://192.168.1.61:8001/access/check`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "cardId": "RFID-2026-001",
  "gateId": "GATE-01",
  "direction": "IN",
  "idempotencyKey": "9f666062-a41d-63f6-c938-668877662222"
}
```
- **Cam kết SLA**: Phản hồi trong ≤ 200ms.
- **Xử lý ngoại lệ**: Áp dụng cơ chế **Fail-closed**, tự động gán `result = "DENY"` khi có lỗi kết nối hoặc timeout quá 1.5 giây.
