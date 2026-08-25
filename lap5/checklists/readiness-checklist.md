# Readiness Checklist — Lab05 (team-gate)

Tick vào từng mục sau khi đã verify thật trên máy (không tick khống).

- [✓] **DB sẵn sàng** — `docker exec -it fit4110-db-lab05 pg_isready -U $env:POSTGRES_USER` trả `accepting connections`
- [✓] **gate-worker sẵn sàng** — `curl http://localhost:9000/health` trả `200 {"status":"ok",...}`
- [✓] **Token đúng** — `.env` có `ACCESS_GATE_API_TOKEN` / `AUTH_TOKEN` khớp với `postman/environments/lab05_local.postman_environment.json`
- [✓] **Port đúng** — API expose `8000`, gate-worker expose `9000`, không xung đột với service khác đang chạy
- [✓] **Network hoạt động** — `api` gọi được `gate-worker` qua tên container (`http://gate-worker:9000`) trong mạng `team-internal`, không qua `localhost`
- [✓] **Version/tag đúng quy ước** — image build/push với tag `v0.1.0-team-gate`

## Cách verify từng mục

```powershell
docker compose up -d --build
docker compose ps
docker exec -it fit4110-db-lab05 pg_isready -U access_gate_user
curl http://localhost:9000/health
curl http://localhost:8000/health
npm run test:local  # hoặc make test-compose
```
