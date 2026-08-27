# RUN.md — mqtt_listener (AccessGate Service, team-gate)

Service nhận UID RFID từ HiveMQ, đối chiếu whitelist, publish kết quả xử lý.

## Chạy local (không Docker) — để test nhanh

```powershell
cd lap6
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Mở `.env`, điền `MQTT_PASSWORD` thật (credential thầy gửi qua tài liệu, **không commit file .env**).

```powershell
$env:MQTT_HOST="f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud"
$env:MQTT_PORT="8883"
$env:MQTT_USE_TLS="true"
$env:MQTT_USERNAME="DVKN2026"
$env:MQTT_PASSWORD="<password-that>"
python -m src.mqtt_listener.main
```

Nếu kết nối đúng, sẽ thấy log:
```
[INFO] Da load 10 UID tu whitelist: data/uid_whitelist.csv
[INFO] Ket noi MQTT: Success
[INFO] Da subscribe topic: smart-campus/raw/access/rfid-uid
```

Sau ~10s, Pi RFID Simulator của thầy sẽ tự đẩy event, log sẽ hiện:
```
[INFO] UID=04:A1:B2:C3:D4:0X -> granted (uid_matched) | door=gate-a | published to smart-campus/events/access
```

## Chạy bằng Docker

```powershell
docker build -t team-gate/mqtt-listener:v0.1.0 .
docker run --rm --env-file .env -v ${PWD}/data:/app/data team-gate/mqtt-listener:v0.1.0
```

## Verify bằng cách subscribe topic output (dùng mosquitto_sub hoặc MQTT Explorer)

Nếu có mosquitto-clients cài sẵn:
```powershell
mosquitto_sub -h f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud -p 8883 --cafile <ca-cert-neu-can> -u DVKN2026 -P "<password-that>" -t "smart-campus/events/access"
```
Hoặc dùng app **MQTT Explorer** (GUI, dễ hơn) — kết nối bằng thông tin trong `.env`, subscribe `smart-campus/events/access`, xem event xuất hiện mỗi ~10s.

## Đã test logic (sandbox, dùng broker Mosquitto local giả lập, KHÔNG dùng credential thật)

- UID hợp lệ (`04:A1:B2:C3:D4:03`) → `granted`, `uid_matched`, đúng tên/lớp từ CSV
- UID lạ (`7A:9B:11:22:33:04`) → `denied`, `uid_not_found`, các field student = null

## Lưu ý bảo mật

- **Không commit `.env`** — đã có trong `.gitignore`
- Password HiveMQ chỉ điền trong `.env` cục bộ, không paste vào code, không paste vào chat công khai/README
