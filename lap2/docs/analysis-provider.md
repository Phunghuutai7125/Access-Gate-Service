# Phân tích yêu cầu — vai Provider

- Cặp đàm phán: Pair 03 — Core Business → Access Gate
- Product: A / B
- Provider service: Access Gate
- Consumer service: Core Business
- Người viết: Phùng Hữu Tài
- Ngày: 11/8/2026

---

## 1. Resource chính

| Resource | Mô tả | Thuộc tính bắt buộc | Thuộc tính tùy chọn |
|---|---|---|---|
| `AccessLog` | Log sự kiện quẹt thẻ ra/vào | logId, cardId, gateId, direction, timestamp, status | reasonCode, operatorNote |
| `GateStatus` | Trạng thái hiện tại của 1 cổng | gateId, state, updatedAt | lastCardId |
| `Card` | Thông tin thẻ và người sở hữu | cardId, personId, cardType, status | issuedAt, expiresAt |

---

## 2. Action/API dự kiến

| Method | Path | Mục đích | Consumer gọi khi nào? |
|---|---|---|---|
| GET | `/access/logs/recent` | Lấy danh sách log gần nhất | Khi Core Business cần audit theo thời gian thực |
| GET | `/access/logs/{logId}` | Lấy chi tiết 1 log cụ thể | Khi cần tra cứu chi tiết 1 sự kiện cụ thể (audit sâu) |
| GET | `/gates/{gateId}/status` | Lấy trạng thái hiện tại của 1 cổng | Khi Core Business cần biết cổng đang mở/đóng/lỗi |
| GET | `/cards/{cardId}` | Lấy thông tin 1 thẻ | Khi Core Business cần xác minh thông tin chủ thẻ |

---

## 3. Error case

| Status | Tình huống | Response body dự kiến |
|---:|---|---|
| 400 | Query parameter sai định dạng (VD: `gateId` rỗng) | `Problem` |
| 401 | Thiếu Bearer token | `Problem` |
| 403 | Token hợp lệ nhưng Core Business không có quyền đọc log | `Problem` |
| 404 | `logId` hoặc `cardId` không tồn tại | `Problem` |
| 409 | Không áp dụng cho GET (để trống hoặc ghi "N/A — endpoint chỉ đọc") |
| 422 | `gateId` đúng format nhưng không tồn tại trong hệ thống | `Problem` |

---

## 4. Giả định bổ sung

- Giả định 1: `GET /access/logs/recent` mặc định trả về log của **24 giờ gần nhất**, có thể lọc thêm qua query parameter `from`/`to` nếu Consumer cần
- Giả định 2: Access Gate lưu log tối thiểu **90 ngày** trước khi archive, đủ cho nhu cầu audit thông thường của Core Business
- Giả định 3: `status` trong response sẽ dùng enum cố định (`granted`/`denied`), không trả trực tiếp giá trị boolean `access_granted` thô để tránh Consumer hiểu sai kiểu dữ liệu

---

## 5. Câu hỏi cho Consumer

1. Core Business có cần phân trang (`pagination`) cho `GET /access/logs/recent` không, hay chỉ cần giới hạn số lượng cố định (VD: 50 log gần nhất)?
2. Naming convention Core Business mong muốn là `camelCase` hay Access Gate giữ nguyên `snake_case` như thiết kế nội bộ hiện tại?
3. Core Business có cần trường `operatorNote` không — nếu có, ai chịu trách nhiệm ghi giá trị này (admin thủ công hay hệ thống tự sinh)?

---

## 6. Rủi ro tích hợp

| Rủi ro | Tác động | Đề xuất xử lý |
|---|---|---|
| Tên field không thống nhất (`card_id` vs `cardId`) | Consumer parse lỗi | Chốt naming trong `openapi.yaml` — ưu tiên `camelCase` vì Core Business đã yêu cầu trong user story |
| `GET /access/logs/recent` trả về quá nhiều dữ liệu nếu không giới hạn | Timeout hoặc mock lỗi khi test bằng Prism | Bắt buộc có `limit` mặc định (VD: 50) và tối đa (VD: 200) trong query parameter |
| `status` không có enum cố định | Core Business hiển thị sai trạng thái nghiệp vụ | Định nghĩa enum rõ trong `components/schemas`: `granted`, `denied`, `pending` |