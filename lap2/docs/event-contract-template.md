# Event Contract sơ bộ — dùng cho dependency Queue async

> File này chỉ dùng cho các cặp Queue async ở Lab 02 để ghi nhận thỏa thuận ban đầu. Đặc tả chi tiết bằng AsyncAPI sẽ chuyển sang Lab 03.

## 1. Thông tin dependency

- Dependency số: 09
- Producer: Access Gate
- Consumer: Analytics
- Cơ chế: Queue async
- Event/topic dự kiến: `access.log.created` (và `access.denied` cho lượt bị từ chối)
- Người ghi: [Tên bạn]
- Ngày: 13/08/2026

## 2. Mục đích nghiệp vụ

Mỗi khi có người quẹt thẻ ra/vào tại một cổng, Access Gate phát event ghi nhận lượt truy cập đó (hoặc lượt bị từ chối). Analytics lắng nghe event này để tổng hợp KPI lượt ra/vào theo thời gian, theo cổng, và theo loại người dùng, đồng thời tính tỷ lệ truy cập bị từ chối, phục vụ dashboard thống kê realtime của Smart Campus.

## 3. Event name / topic

| Mục | Giá trị |
|---|---|
| Event name | `access.log.created`, `access.denied` |
| Topic/queue | `access.events` |
| Producer | `access-gate` |
| Consumer | `analytics` |

## 4. Payload tối thiểu

```json
{
  "eventId": "770e8400-e29b-41d4-a716-446655440002",
  "eventType": "access.log.created",
  "occurredAt": "2026-08-11T03:25:30Z",
  "correlationId": "9f666062-a41d-63f6-c938-668877662222",
  "source": "access-gate",
  "data": {
    "gate_id": "GATE-01",
    "direction": "IN",
    "card_id_hash": "sha256:abc123...",
    "user_type": "student",
    "recorded_at": "2026-08-11T03:25:30Z"
  }
}
```

## 5. Ràng buộc cần thống nhất

| Vấn đề | Quyết định tạm thời |
|---|---|
| Event id có bắt buộc không? | Có — `eventId` dạng UUID, bắt buộc mỗi event |
| Có cần correlationId không? | Có — dùng để trace xuyên suốt hệ thống, liên kết với request gốc |
| Có cho phép gửi trùng event không? | Có thể xảy ra do retry mạng, Analytics phải xử lý idempotent dựa trên `eventId` |
| Retry khi lỗi | Ghi rõ ở Lab 03 |
| Dead-letter queue | Ghi rõ ở Lab 03 |
| Naming convention trong `data` | Đã thống nhất với Analytics: dùng `snake_case` (khác với `openapi.yaml` REST dùng `camelCase`) — do Analytics là bên quyết định format tiêu thụ |
| Direction (IN/OUT hay ENTER/EXIT) | Đồng ý dùng `IN` / `OUT` theo đề xuất của Analytics |
| Card ID có hash không | Đồng ý dùng `card_id_hash` thay vì `card_id` gốc, để tránh lộ dữ liệu định danh |
| Quẹt thẻ lỗi kỹ thuật có tạo `access.log.created` không | Nếu hợp lệ → `access.log.created`; nếu bị từ chối do policy → `access.denied`; nếu lỗi kỹ thuật không xác định được → cần thống nhất riêng, chưa chốt |

## 6. Issue chuyển sang Lab 03

1. Định nghĩa chính thức AsyncAPI cho topic `access.events`, bao gồm schema đầy đủ (không chỉ ví dụ payload tối thiểu)
2. Xác định cơ chế retry cụ thể khi Analytics không nhận được event (số lần thử lại, khoảng cách giữa các lần)
3. Xác định dead-letter queue — event nào sau N lần retry thất bại sẽ được đưa vào đâu để xử lý thủ công
4. Xác nhận broker thực tế sẽ dùng (RabbitMQ, Kafka, hay công nghệ khác) và cấu hình topic/exchange tương ứng