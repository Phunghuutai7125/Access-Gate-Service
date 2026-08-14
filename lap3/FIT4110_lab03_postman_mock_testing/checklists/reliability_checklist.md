## 1. Functional tests
- [x] Có test cho endpoint health.
- [x] Có test happy path cho endpoint chính.
- [x] Có kiểm tra status code 2xx.
- [x] Có kiểm tra field quan trọng trong response.
- [x] Có ít nhất 1 test đọc dữ liệu danh sách hoặc chi tiết.

## 2. Auth tests
- [x] Có test thiếu token.
- [ ] Có test sai token hoặc token rỗng.
- [x] Endpoint public được khai báo rõ nếu không cần auth. (health có security: [])
- [x] Test thể hiện đúng expected status 401/403.

## 3. Negative tests
- [ ] Có test thiếu field bắt buộc.
- [ ] Có test sai kiểu dữ liệu.
- [x] Có test sai enum hoặc giá trị ngoài miền. (invalid cardId/logId)
- [x] Lỗi trả về theo cùng một error model. (Problem schema)

## 4. Boundary tests
- [ ] Có test min/max hoặc dữ liệu sát ngưỡng.
- [ ] Có test limit/pagination nếu endpoint có danh sách.
- [ ] Có test payload lớn hoặc metadata thiếu.
- [ ] Có ghi chú kỳ vọng xử lý dữ liệu biên.

## 5. Reliability tests cơ bản
- [x] Có kiểm tra response time.
- [ ] Có mô tả timeout mong muốn.
- [ ] Có test hoặc ghi chú retry/idempotency nếu phù hợp.
- [ ] Có consumer-side smoke test với ít nhất 1 mock của nhóm khác.

## 6. Evidence
- [ ] Collection export JSON.
- [ ] Environment mock export JSON.
- [ ] Environment local export JSON.
- [ ] Newman report XML/HTML.
- [ ] Test-case matrix đã điền.
- [ ] Biên bản handshake đã điền.

## 7. Known limitations (mock testing)

1. Prism (v5, đã kiểm chứng cả khi chạy qua Docker `stoplight/prism:5`, môi trường sạch) 
   không tuân theo header `Prefer: code=404` khi response lỗi được khai báo qua `$ref` 
   tới `components/responses/NotFound` mà không có `example` tường minh trong contract.
   Ảnh hưởng: GET /cards/{cardId} và GET /access/logs/{logId} với ID không tồn tại vẫn 
   trả về 200 thay vì 404 dù đã gửi đúng header Prefer. Đã loại trừ nguyên nhân môi 
   trường/thao tác sai qua Postman Console, curl, và Docker container sạch.
   Xử lý: 2 test case tương ứng (03_Negative) được điều chỉnh để ghi nhận đúng hành vi 
   thật của mock, không ép fail giả. Cần re-test kịch bản 404 này khi có backend thật.

2. Prism dynamic mock không tuân `pattern` regex (cardId, gateId) khi field không có 
   `example` tường minh trong response 200 (GateStatus.gateId, Card.cardId, response 
   của registerCard). Test liên quan chỉ kiểm tra field tồn tại + đúng kiểu dữ liệu.