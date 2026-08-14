\# Consumer-Provider Handshake — Access Gate Service (team-gate)



\## Thông tin chung

\- Provider: Access Gate Service (team-gate)

\- Contract: contracts/team-gate.openapi.yaml

\- Ngay xac nhan: 2026-08-14

\- Muc dich: Xac nhan Consumer va Provider thong nhat ve API contract truoc khi tich hop.



\## Danh sach endpoint duoc cong bo

| Endpoint | Method | Muc dich | Consumer chinh |

|---|---|---|---|

| /health | GET | Health check | Moi service (monitoring) |

| /access/logs/recent | GET | Lay danh sach log ra/vao | Core Business |

| /access/logs/{logId} | GET | Lay chi tiet 1 log | Core Business |

| /gates/{gateId}/status | GET | Lay trang thai cong | Core Business |

| /cards/{cardId} | GET | Xac minh thong tin the | Core Business |

| /cards | POST | Dang ky the moi | Admin module |



\## Xac nhan tu Provider (team-gate)

\- \[x] Contract da lint PASS (Spectral, 0 error).

\- \[x] Contract da duoc mock qua Prism, kiem thu qua Postman + Newman (13 request, 40 assertion, 0 fail).

\- \[x] Cac gioi han cua mock da duoc ghi nhan trong reliability-checklist.md, khong anh huong toi tinh dung dan cua contract.

\- \[x] Environment mock va local da san sang, Consumer co the tich hop thu qua mock truoc khi Provider hoan thanh backend that.



\## Xac nhan tu Consumer (Core Business - gia dinh, dien khi co xac nhan that)

\- \[ ] Da xem va dong y contract team-gate.openapi.yaml.

\- \[ ] Da thu goi qua mock server (Prism, http://127.0.0.1:4010).

\- \[ ] Khong co yeu cau thay doi field/response.

\- \[ ] San sang tich hop khi Provider co backend that.



\## Ghi chu

Tai lieu nay se duoc cap nhat khi co xac nhan chinh thuc tu doi Consumer 

(vi du: chu ky, email xac nhan, hoac bien ban hop nhom).

