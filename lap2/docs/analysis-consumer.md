# Phân tích yêu cầu — vai Consumer

Phân tích yêu cầu — vai Consumer
Cặp đàm phán: Pair 10 — Access Gate → Core Business

Product: A

Consumer service: Access Gate Service

Provider service: Core Business Service

Người viết:nguyễn quang duy

Ngày: 11-8-2026

---

# Phân tích yêu cầu — vai Consumer

- Cặp đàm phán: Pair 03: Core - Access Gate[cite: 1]
- Product: A
- Consumer service: Access Gate Service
- Provider service: Core Business Service
- Người viết: Anh Tú / Kiên
- Ngày: 2026-05-02

---

## 1. Resource Consumer cần nhận/gửi

| Resource | Consumer dùng để làm gì? | Field bắt buộc với Consumer | Field có thể tùy chọn |
|---|---|---|---|
| AccessCheck | Gửi yêu cầu kiểm tra quyền quẹt thẻ realtime của người dùng tại cổng | cardId, gateId, direction, timestamp, personId | deviceIp, notes |
| PolicyDetail | Tra cứu chi tiết thông tin chính sách khi cần audit hoặc kiểm tra bổ sung | policyId | description, validDays |

---

## 2. API Consumer cần gọi

| Method | Path | Lúc nào gọi? | Kỳ vọng response |
|---|---|---|---|
| POST | `/access/check` | Ngay khi có sự kiện quẹt thẻ từ thiết bị đọc thẻ (`RFID Reader`) | Trả về kết quả quyết định (`allow/deny`), mã lý do (`reasonCode`) và thời hạn cache (`expiresAt`) |
| GET | `/policies/access/{policyId}` | Khi Access Gate cần lấy thông tin chi tiết của policy được áp dụng | Trả về thông tin chi tiết cấu hình chính sách |
| GET | `/health` | Kiểm tra định kỳ xem Core Business có đang hoạt động ổn định hay không | HTTP Status `200 OK` |

---

## 3. Error case Consumer cần xử lý

Tối thiểu 5 case.

| Status | Consumer hiểu là gì? | Consumer sẽ xử lý thế nào? |
|---:|---|---|
| 400 | Request sai schema / thiếu trường dữ liệu | Ghi log lỗi cấu trúc, từ chối yêu cầu và báo lỗi hệ thống cục bộ |
| 401 | Thiếu token hoặc Token không hợp lệ | Cấu hình lại thông tin xác thực/bearer token hệ thống |
| 403 | Không đủ quyền gọi dịch vụ Core Business | Kích hoạt cảnh báo bảo mật, thông báo admin hệ thống |
| 404 | Không tìm thấy Policy hoặc Resource yêu cầu | Hiển thị trạng thái lỗi cấu hình chính sách không tồn tại |
| 409 | Xung đột nghiệp vụ / Trạng thái thẻ không đồng bộ | Yêu cầu kiểm tra lại trạng thái thẻ hoặc thực hiện thao tác đồng bộ |
| 422 | Vi phạm rule nghiệp vụ (VD: Thẻ hết hạn/Đã khóa) | Hiển thị đúng `reasonCode` từ chối qua cổng cho người quẹt thẻ biết |

---

## 4. Giả định bổ sung

- Giả định 1: Access Gate Service đã thực hiện validate sơ bộ thông tin thẻ nội bộ (tồn tại, active) trước khi đẩy request sang Core Business để kiểm tra policy.
- Giả định 2: Hệ thống mạng nội bộ giữa Access Gate và Core Business có độ ổn định cao, đáp ứng được yêu cầu về tốc độ phản hồi thấp.
- Giả định 3: Quyết định trả về từ Core Business có kèm thời gian hiệu lực (`expiresAt`) để Access Gate có thể tối ưu hóa hiệu năng bằng cách cache tạm thời.

---

## 5. Câu hỏi cho Provider

1. Timeout tối đa của `/access/check` là bao nhiêu? — Cần con số cụ thể (VD: 500ms, 1s) vì ảnh hưởng trực tiếp trải nghiệm người dùng đứng chờ ở cổng.
2. Khi Core Business lỗi/timeout thì Access Gate xử lý ra sao — fail-open (cho qua) hay fail-closed (chặn lại)? — Đây là quyết định an ninh quan trọng nhất cần chốt.
3. Có cần `idempotencyKey` cho mỗi lượt quẹt không? — Để tránh xử lý lặp nếu Access Gate thực hiện retry do timeout.
4. `reasonCode` có bộ giá trị cố định (enum) không, hay là free text? — Cần enum cố định để Access Gate hiển thị đúng thông báo cho người dùng.
5. Định dạng cấu trúc lỗi khi request gặp sự cố (400, 422) là gì? — Thống nhất chuẩn phản hồi lỗi Problem Details.

---

## 6. Rủi ro tích hợp

| Rủi ro | Tác động | Đề xuất xử lý |
|---|---|---|
| Provider đổi kiểu dữ liệu hoặc tên field phản hồi | Access Gate parse dữ liệu bị lỗi, hệ thống không mở cổng | Chốt cứng type/format/pattern thông qua hợp đồng OpenAPI |
| Provider phản hồi chậm gây treo hệ thống ở cổng | Người dùng đứng chờ lâu, gây ùn tắc tại cửa ra/vào | Thống nhất rõ ràng timeout tối đa và cơ chế xử lý lỗi khi quá hạn |
| Provider thiếu mã lỗi chi tiết | Access Gate không phân biệt được nguyên nhân để hiển thị thông báo | Thống nhất danh mục `reasonCode` và chuẩn hóa Problem Details |
