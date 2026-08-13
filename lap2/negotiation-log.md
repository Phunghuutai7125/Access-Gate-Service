# Biên bản đàm phán hợp đồng API

- Cặp đàm phán: Core Business ↔ Access Gate (Cặp #3 & #10)
- Product: Access Control / Gate Access Service
- Provider: Core Business (cho cặp #10) / Access Gate (cho cặp #3)
- Consumer: Access Gate (cho cặp #10) / Core Business (cho cặp #3)
- Phiên: v1.0
- Ngày: 2026-08-11

---

## Issue #1

- Raised by: Core Business (Provider)
- Endpoint: POST /access/check
- Concern: Khi Core timeout > 200ms hoặc trả về lỗi 500, Access Gate có thể mở cổng không an toàn.
- Proposal: Áp dụng fallback policy Fail-closed, tức là đóng cổng khi Core không phản hồi hợp lệ.
- Resolution: Accepted
- Rationale: Đảm bảo an toàn an ninh và tránh mở cổng trong tình huống lỗi hệ thống.
- Impact: Nếu Core bị lỗi/timed out thì lượt quẹt sẽ bị từ chối mở cổng.

---

## Issue #2

- Raised by: Core Business (Provider)
- Endpoint: POST /access/check và các response JSON liên quan
- Concern: Contract hiện tại cần thống nhất định dạng JSON để tránh sai lệch giữa các hệ thống.
- Proposal: Dùng camelCase cho tất cả field JSON như cardId, gateId, idempotencyKey.
- Resolution: Accepted
- Rationale: Đồng bộ naming convention giữa Core và Access Gate và giảm rủi ro tích hợp.
- Impact: Tất cả request/response JSON cần tuân thủ camelCase.

---

## Issue #3

- Raised by: Core Business (Provider)
- Endpoint: POST /access/check
- Concern: Nếu mạng bị retry, cùng một lần quẹt thẻ có thể bị xử lý trùng dẫn đến hành động không nhất quán.
- Proposal: Access Gate gửi kèm một UUID idempotencyKey cho mỗi lượt quẹt và Core dùng để deduplicate.
- Resolution: Accepted
- Rationale: Tránh xử lý trùng khi retry mạng và đảm bảo tính nhất quán của quyết định mở/khóa cổng.
- Impact: Request bắt buộc phải có trường idempotencyKey theo định dạng UUID.

---

## Issue #4

- Raised by: Core Business (Consumer)
- Endpoint: GET /access/logs/recent, GET /access/logs/{logId}
- Concern: Core cần tra cứu audit log từ Access Gate để kiểm tra lịch sử quẹt thẻ và theo dõi sự kiện.
- Proposal: Access Gate hỗ trợ filter theo startTime và endTime, đồng thời lưu log tối thiểu 30 ngày.
- Resolution: Accepted
- Rationale: Đáp ứng nhu cầu audit, troubleshooting và kiểm tra lịch sử hoạt động của hệ thống.
- Impact: Core có thể query log theo khoảng thời gian và truy xuất dữ liệu trong khoảng lưu trữ tối thiểu 30 ngày.

---

## Issue #5

- Raised by: Consumer / Provider
- Endpoint:
- Concern:
- Proposal:
- Resolution: Accepted / Rejected / Modified
- Rationale:
- Impact:

---

## Issue #6

- Raised by: Consumer / Provider
- Endpoint:
- Concern:
- Proposal:
- Resolution: Accepted / Rejected / Modified
- Rationale:
- Impact:

---

# Chốt hợp đồng v1.0

Provider sign-off:  
Consumer sign-off:  
Witness (GV/TA):    
Date:               

---

## Ghi chú warning nếu Spectral còn cảnh báo

| Warning | Lý do chấp nhận tạm thời | Kế hoạch sửa |
|---|---|---|
|  |  |  |
