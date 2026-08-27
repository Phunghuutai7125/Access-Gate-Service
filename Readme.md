# 🚪 ACCESS GATE SYSTEM

> **Hệ thống kiểm soát ra/vào bằng Access Gate**

# 🚪 ACCESS GATE SYSTEM

### Môn học: Dịch vụ kết nối và Công nghệ nền tảng

---
**Thành Viên Nhóm**
| STT | Họ và tên         | Đóng Góp              |
| --: | ----------------- | --------------------- |
|   1 | Phùng Hữu Tài.    | 40%                   |
|   2 | Nguyễn Mạnh Cường | 30%                   |
|   3 | Nguyễn Quang Duy  | 30%                   |

## 1. Giới thiệu

**Access Gate System** là một hệ thống quản lý và kiểm soát truy cập được xây dựng trong khuôn khổ môn học **Dịch vụ kết nối và Công nghệ nền tảng**.

Hệ thống mô phỏng quá trình kết nối giữa **thiết bị Access Gate, Backend Services, Database và giao diện quản trị** thông qua mạng máy tính và các dịch vụ API.

Mục tiêu chính của project là áp dụng các kiến thức về:

* Network Communication
* Client – Server Architecture
* RESTful API
* Service Communication
* Database Services
* Containerization
* Docker
* Docker Compose
* Authentication & Authorization
* Health Check
* Service Monitoring

---

# 2. Mục tiêu

Project hướng tới xây dựng một nền tảng có khả năng:

* Quản lý Access Gate.
* Kết nối thiết bị với Backend.
* Cung cấp REST API.
* Xác thực request từ thiết bị.
* Kiểm tra quyền truy cập.
* Lưu trữ lịch sử truy cập.
* Quản lý người dùng.
* Theo dõi trạng thái các service.
* Triển khai hệ thống bằng Docker.
* Cho phép các service giao tiếp với nhau thông qua network.

---

# 3. Kiến trúc hệ thống

Hệ thống được thiết kế theo mô hình nhiều service:

```text
                    ┌──────────────────┐
                    │      CLIENT      │
                    │  Web / Browser   │
                    └────────┬─────────┘
                             │
                           HTTP
                             │
                             ▼
                    ┌──────────────────┐
                    │    API GATEWAY   │
                    │    / BACKEND     │
                    └────────┬─────────┘
                             │
             ┌───────────────┼───────────────┐
             │               │               │
             ▼               ▼               ▼
      ┌────────────┐  ┌────────────┐  ┌────────────┐
      │ Auth       │  │ Access     │  │ Gate       │
      │ Service    │  │ Service    │  │ Service    │
      └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │     DATABASE     │
                    │ MySQL/PostgreSQL │
                    └──────────────────┘

                    Docker Network
                    ─────────────────
```

---

# 4. Các thành phần chính

## 4.1. Client

Client có thể là:

* Web Browser
* Access Gate Device
* API Client
* Postman

Client gửi request đến Backend thông qua HTTP/HTTPS.

Ví dụ:

```http
POST /api/access/check
```

---

## 4.2. Backend Service

Backend đóng vai trò trung tâm của hệ thống.

Các nhiệm vụ chính:

* Nhận request.
* Xác thực request.
* Kiểm tra quyền.
* Xử lý nghiệp vụ.
* Giao tiếp với Database.
* Giao tiếp với các service khác.
* Trả response cho Client.

---

## 4.3. Access Gate Service

Access Gate Service quản lý thông tin các Gate.

Thông tin có thể bao gồm:

```text
Gate ID
Gate Name
IP Address
MAC Address
Status
Location
Last Connected
```

Service có khả năng kiểm tra trạng thái:

```text
ONLINE
OFFLINE
ERROR
```

---

## 4.4. Authentication Service

Authentication Service chịu trách nhiệm xác thực người dùng.

Quá trình:

```text
Client
   │
   │ Login
   ▼
Auth Service
   │
   │ Validate
   ▼
Database
   │
   ▼
Token
   │
   ▼
Client
```

Hệ thống có thể sử dụng:

* JWT
* Access Token
* Password Hashing
* Role-Based Authentication

---

# 5. Service Communication

Một nội dung quan trọng của project là **kết nối giữa các dịch vụ**.

Ví dụ:

```text
Access Gate
     │
     │ HTTP Request
     ▼
Access Service
     │
     │ Request
     ▼
Auth Service
     │
     │ Verify
     ▼
Database
```

Các service giao tiếp thông qua:

```text
HTTP
REST API
TCP/IP
Docker Network
```

---

# 6. RESTful API

Hệ thống sử dụng REST API để cung cấp dịch vụ.

## Authentication

```http
POST /api/auth/login
```

## User

```http
GET    /api/users
POST   /api/users
GET    /api/users/{id}
PUT    /api/users/{id}
DELETE /api/users/{id}
```

## Gate

```http
GET    /api/gates
POST   /api/gates
GET    /api/gates/{id}
PUT    /api/gates/{id}
DELETE /api/gates/{id}
```

## Access

```http
POST /api/access/check
```

## Access Logs

```http
GET /api/access-logs
```

## Health Check

```http
GET /health
```

---

# 7. Ví dụ Access Request

Khi người dùng thực hiện truy cập:

```json
{
  "user_id": 1001,
  "gate_id": 1,
  "method": "RFID"
}
```

Backend xử lý:

```text
Receive Request
       │
       ▼
Authenticate
       │
       ▼
Check User
       │
       ▼
Check Permission
       │
       ▼
Check Gate
       │
       ▼
Access Decision
       │
   ┌───┴────┐
   ▼        ▼
GRANTED   DENIED
```

Response:

```json
{
  "success": true,
  "result": "GRANTED",
  "gate_id": 1
}
```

---

# 8. Database Service

Database lưu trữ dữ liệu của hệ thống.

Các bảng chính:

```text
Users
Gates
Roles
Permissions
AccessLogs
Devices
```

Quan hệ cơ bản:

```text
Users
  │
  ├──────── Roles
  │
  └──────── AccessLogs
                 │
                 ▼
               Gates
```

---

# 9. Docker

Project sử dụng **Docker** để đóng gói các thành phần của hệ thống.

Ví dụ:

```text
Docker
│
├── Backend Container
│
├── Database Container
│
├── Frontend Container
│
└── Other Services
```

Ưu điểm:

* Môi trường chạy đồng nhất.
* Dễ triển khai.
* Dễ quản lý service.
* Dễ mở rộng.
* Tách biệt các thành phần.
* Có thể chạy toàn bộ hệ thống bằng Docker Compose.

---

# 10. Docker Compose

Ví dụ kiến trúc:

```yaml
services:

  backend:
    build: ./backend
    ports:
      - "8000:8000"

  database:
    image: mysql
    ports:
      - "3306:3306"

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
```

Các service sử dụng chung Docker Network:

```text
access-network
```

Nhờ đó Backend có thể kết nối Database bằng service name:

```text
database:3306
```

thay vì phải sử dụng IP cố định.

---

# 11. Network Architecture

Kiến trúc mạng:

```text
                 INTERNET / LAN
                       │
                       ▼
                ┌─────────────┐
                │   Gateway   │
                └──────┬──────┘
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
        Access Gate         Server
              │                 │
              │                 │
              └───────┬─────────┘
                      │
                      ▼
               Docker Network
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
          Backend   Database  Frontend
```

---

# 12. Health Check

Mỗi service cần có cơ chế kiểm tra trạng thái.

Ví dụ:

```http
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

Docker có thể sử dụng Health Check để xác định service đang hoạt động.

Ví dụ:

```text
Backend
   │
   ├── HEALTHY
   │
   └── UNHEALTHY
```

---

# 13. Environment Configuration

Các thông tin cấu hình được đặt trong `.env`.

Ví dụ:

```env
APP_PORT=8000

DATABASE_HOST=database
DATABASE_PORT=3306
DATABASE_NAME=access_gate
DATABASE_USER=root
DATABASE_PASSWORD=password

JWT_SECRET=your_secret_key
```

Không commit file `.env` thật lên GitHub.

Sử dụng:

```text
.env.example
```

để cung cấp cấu hình mẫu.

---

# 14. Cài đặt

## Bước 1: Clone project

```bash
git clone <repository-url>

cd access-gate
```

## Bước 2: Tạo file environment

```bash
cp .env.example .env
```

## Bước 3: Build Docker

```bash
docker compose build
```

## Bước 4: Khởi động hệ thống

```bash
docker compose up -d
```

## Bước 5: Kiểm tra service

```bash
docker compose ps
```

## Bước 6: Xem log

```bash
docker compose logs -f
```

---

# 15. Kiểm thử API

Có thể sử dụng:

* Postman
* Swagger
* Browser
* cURL

Ví dụ:

```bash
curl http://localhost:8000/health
```

Kết quả:

```json
{
  "status": "healthy"
}
```

Swagger:

```text
http://localhost:8000/docs
```

---

# 16. Kiểm thử kết nối Service

Kiểm tra Backend:

```bash
docker compose ps
```

Kiểm tra network:

```bash
docker network ls
```

Kiểm tra container:

```bash
docker ps
```

Kiểm tra log:

```bash
docker compose logs backend
```

Kiểm tra Database:

```text
Backend
   │
   │ TCP/IP
   ▼
Database
```

---

# 17. Bảo mật

Hệ thống áp dụng một số cơ chế bảo mật:

* Authentication.
* Authorization.
* JWT.
* Password Hashing.
* Input Validation.
* Role-Based Access Control.
* Environment Variables.
* Không lưu password dạng plaintext.
* Không commit secret lên GitHub.
* Giới hạn quyền truy cập Database.

---

# 18. Cấu trúc thư mục

```text
access-gate/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── database/
│   │
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── Dockerfile
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── network.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

# 19. Kết quả đạt được

Sau khi hoàn thành, hệ thống có khả năng:

* [x] Xây dựng kiến trúc Client – Server.
* [x] Xây dựng REST API.
* [x] Kết nối Backend với Database.
* [x] Kết nối các service thông qua Network.
* [x] Quản lý Access Gate.
* [x] Kiểm tra quyền truy cập.
* [x] Lưu Access Logs.
* [x] Authentication.
* [x] Health Check.
* [x] Docker Containerization.
* [x] Docker Compose.
* [x] Service Monitoring.

---

# 20. Hướng phát triển

Trong tương lai hệ thống có thể mở rộng:

* Microservices Architecture.
* API Gateway.
* Message Queue.
* Redis Cache.
* MQTT cho IoT Access Gate.
* WebSocket cho Real-time Monitoring.
* Kubernetes.
* Cloud Deployment.
* Monitoring với Prometheus/Grafana.
* Centralized Logging.
* CI/CD Pipeline.
* HTTPS/TLS.
* Multi-Gate Management.

---

# 21. Công nghệ

| Thành phần      | Công nghệ               |
| --------------- | ----------------------- |
| Backend         | FastAPI / Flask         |
| Frontend        | HTML / CSS / JavaScript |
| API             | REST API                |
| Database        | MySQL / PostgreSQL      |
| Container       | Docker                  |
| Orchestration   | Docker Compose          |
| Network         | TCP/IP / HTTP           |
| Authentication  | JWT                     |
| API Testing     | Postman / Swagger       |
| Version Control | Git / GitHub            |

---

# 22. Tổng kết

Project **Access Gate System** được xây dựng nhằm minh họa cách các thiết bị và dịch vụ có thể kết nối với nhau trong một hệ thống nền tảng.

Trọng tâm của project là:

```text
              ACCESS GATE
                   │
                   │
               Network
                   │
                   ▼
              REST API
                   │
          ┌────────┼────────┐
          │        │        │
          ▼        ▼        ▼
        Auth     Access    Gate
       Service   Service  Service
          │        │        │
          └────────┼────────┘
                   │
                   ▼
               Database
                   │
                   ▼
              Dashboard
```

Thông qua project, nhóm áp dụng các kiến thức của môn **Dịch vụ kết nối và Công nghệ nền tảng** vào một bài toán thực tế, tập trung vào **kết nối dịch vụ, giao tiếp API, Network, Database Service, Docker và triển khai hệ thống**.

---

## 📚 Course

**Môn học:** Dịch vụ kết nối và Công nghệ nền tảng

**Project:** Access Gate System

**Academic Year:** 2026

**Team:** Access Gate Team

