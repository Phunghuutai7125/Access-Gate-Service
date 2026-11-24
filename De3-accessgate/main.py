"""
Access Gate Service — FIT4110 BTL
Nhóm: AccessGate

Endpoints:
  GET  /health
  POST /access/swipe              ← Nhận quẹt thẻ, gọi Core Business, ghi log, trả ALLOW/DENY
  GET  /access/logs/recent        ← Core Business đọc log ra/vào (filter startTime/endTime/gateId)
  GET  /access/logs/{logId}       ← Core Business đọc chi tiết 1 log
  GET  /gates/{gateId}/status     ← Core Business kiểm tra trạng thái cổng
  GET  /cards/{cardId}            ← Core Business tra thông tin thẻ
  POST /cards                     ← Đăng ký thẻ mới (STUDENT / STAFF)
"""

# ============================================================
# IMPORTS
# ============================================================
import os
import re
import uuid
import time
import csv
import ssl
import json
import hashlib
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Literal

import httpx
import json
import hashlib
from fastapi import FastAPI, Request, Header, Query, Path, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import create_engine, text
try:
    from paho.mqtt import client as mqtt_client
except ImportError:
    mqtt_client = None

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("access_gate")

# ============================================================
# CONFIGURATION — đọc từ biến môi trường (xem .env.example)
# ============================================================
APP_NAME = "access-gate-service"
API_TOKEN = os.getenv("ACCESS_GATE_API_TOKEN", "dev-secret-token")

# PostgreSQL
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "access_gate_db")
DB_USER     = os.getenv("DB_USER",     "access_gate_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "changeme")
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Core Business — theo đúng spec Core gửi
CORE_BASE_URL       = os.getenv("CORE_BUSINESS_URL", "http://192.168.1.61:8001")
CORE_CHECK_ENDPOINT = f"{CORE_BASE_URL}/access/check"
CORE_TIMEOUT_S      = 1.5     # Timeout gọi Core (SLA ≤ 200ms, nhưng ta chờ tối đa 1.5s)
SLA_WARN_MS         = 200
MOCK_CORE           = os.getenv("MOCK_CORE", "false").lower() == "true"

# Analytics MQTT — theo đúng hợp đồng Pair 09 (Quỳnh Đinh Trọng)
ANALYTICS_MQTT_HOST  = os.getenv("ANALYTICS_MQTT_HOST", "192.168.1.51")
ANALYTICS_MQTT_PORT  = int(os.getenv("ANALYTICS_MQTT_PORT", "1883"))
ANALYTICS_MQTT_TOPIC = os.getenv("ANALYTICS_MQTT_TOPIC", "access.events")
ENABLE_ANALYTICS_MQTT = os.getenv("ENABLE_ANALYTICS_MQTT", "true").lower() == "true"

# HiveMQ Cloud của Giảng viên (Pi RFID Simulator 24/7)
HIVEMQ_HOST         = os.getenv("HIVEMQ_HOST", "f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud")
HIVEMQ_PORT         = int(os.getenv("HIVEMQ_PORT", "8883"))
HIVEMQ_USERNAME     = os.getenv("HIVEMQ_USERNAME", "DVKN2026")
HIVEMQ_PASSWORD     = os.getenv("HIVEMQ_PASSWORD", "ThaiBao12A@")
HIVEMQ_INPUT_TOPIC  = os.getenv("HIVEMQ_INPUT_TOPIC", "smart-campus/raw/access/rfid-uid")
HIVEMQ_OUTPUT_TOPIC = os.getenv("HIVEMQ_OUTPUT_TOPIC", "smart-campus/events/access")
ENABLE_HIVEMQ       = os.getenv("ENABLE_HIVEMQ", "true").lower() == "true"
WHITELIST_PATH      = os.path.join(os.path.dirname(__file__), "data", "Acessgate_uid_whitelist.csv")

# Regex pattern
GATE_ID_RE = re.compile(r"^GATE-[0-9]{2}$")
CARD_ID_RE = re.compile(r"^RFID-[0-9]{4}-[0-9]{3}$")

# ============================================================
# DATABASE — SQLAlchemy Core (không ORM)
# ============================================================
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cards (
    card_id      VARCHAR(20) PRIMARY KEY,
    person_id    VARCHAR(50) NOT NULL,
    card_type    VARCHAR(10) NOT NULL,
    status       VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
    issued_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS gates (
    gate_id      VARCHAR(10) PRIMARY KEY,
    state        VARCHAR(10) NOT NULL DEFAULT 'CLOSED',
    last_card_id VARCHAR(20),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS access_logs (
    log_id       UUID PRIMARY KEY,
    card_id      VARCHAR(20) NOT NULL,
    gate_id      VARCHAR(10) NOT NULL,
    direction    VARCHAR(5)  NOT NULL,
    result       VARCHAR(10) NOT NULL,
    reason_code  VARCHAR(40),
    decision_id  VARCHAR(50),
    operator_note TEXT,
    ts           TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

SEED_SQL = """
INSERT INTO cards (card_id, person_id, card_type, status, issued_at)
VALUES 
    ('RFID-9215-649', 'SV001', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-001', 'SV001', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-002', 'SV002', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-003', 'SV003', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-004', 'SV004', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-005', 'SV005', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-006', 'SV006', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-007', 'SV007', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-008', 'SV008', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-009', 'SV009', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z'),
    ('RFID-2026-010', 'SV010', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z')
ON CONFLICT (card_id) DO NOTHING;

INSERT INTO gates (gate_id, state, last_card_id, updated_at)
VALUES ('GATE-01', 'CLOSED', 'RFID-2026-001', '2026-08-11T07:30:00Z'),
       ('GATE-79', 'CLOSED', 'RFID-9215-649', '2026-08-11T07:30:00Z')
ON CONFLICT (gate_id) DO NOTHING;

INSERT INTO access_logs (log_id, card_id, gate_id, direction, result, reason_code, ts)
VALUES ('3d906e18-c3d6-f4f7-edc7-b1a59761d251',
        'RFID-9215-649', 'GATE-79', 'IN', 'ALLOW', 'VALID_CARD', '2026-08-11T07:30:00Z')
ON CONFLICT (log_id) DO NOTHING;
"""


def wait_for_db_and_init(max_retries: int = 15, delay: float = 2.0):
    """Retry kết nối DB lúc startup — tránh race condition với container postgres."""
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.execute(text(SCHEMA_SQL))
                conn.execute(text(SEED_SQL))
                conn.commit()
            logger.info("Kết nối PostgreSQL thành công (lần %d)", attempt)
            return
        except Exception as exc:
            last_err = exc
            logger.warning("DB chưa sẵn sàng (lần %d/%d): %s", attempt, max_retries, exc)
            time.sleep(delay)
    raise RuntimeError(f"Không kết nối được PostgreSQL sau {max_retries} lần: {last_err}")


# ============================================================
# CORE BUSINESS CLIENT
# Gọi POST /access/check — theo đúng spec Core Business gửi:
#   Request: cardId, gateId, direction, idempotencyKey  (không có timestamp, không có Authorization)
#   Response: decisionId, cardId, gateId, direction, result, reasonCode, policyId, evaluatedAt
#   Fail-closed: mọi lỗi/timeout → result = "DENY"
# ============================================================
def call_core_check(card_id: str, gate_id: str, direction: str) -> dict:
    """
    Trả về dict:
      result      : "ALLOW" | "DENY"
      reasonCode  : string
      decisionId  : string | None
      policyId    : string | None
      evaluatedAt : string | None
      source      : "CORE" | "FALLBACK" | "MOCK_LOCAL"
    """
    def _deny(reason: str) -> dict:
        return {
            "result": "DENY",
            "reasonCode": reason,
            "decisionId": None,
            "policyId": None,
            "evaluatedAt": None,
            "source": "FALLBACK",
        }

    # Nếu bật MOCK_CORE (chế độ test không cần mạng LAN với máy nhóm Core)
    if MOCK_CORE:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with engine.connect() as conn:
            card_row = conn.execute(
                text("SELECT * FROM cards WHERE card_id = :id AND status = 'ACTIVE'"),
                {"id": card_id}
            ).fetchone()

        # Cho phép các thẻ hợp lệ đã seed hoặc có trong database
        if card_row or card_id in ("RFID-2026-001", "RFID-9215-649"):
            logger.info("MOCK_CORE local check: ALLOW cho card=%s", card_id)
            return {
                "result": "ALLOW",
                "reasonCode": "VALID_CARD",
                "decisionId": f"mock-{uuid.uuid4().hex[:12]}",
                "policyId": "POL-MOCK-001",
                "evaluatedAt": now_iso,
                "source": "MOCK_LOCAL",
            }
        else:
            logger.info("MOCK_CORE local check: DENY cho card=%s", card_id)
            return {
                "result": "DENY",
                "reasonCode": "UNKNOWN_CARD",
                "decisionId": f"mock-{uuid.uuid4().hex[:12]}",
                "policyId": None,
                "evaluatedAt": now_iso,
                "source": "MOCK_LOCAL",
            }

    payload = {
        "cardId": card_id,
        "gateId": gate_id,
        "direction": direction,
        "idempotencyKey": str(uuid.uuid4()),
    }
    headers = {"Content-Type": "application/json"}

    start = datetime.now()
    try:
        with httpx.Client(timeout=CORE_TIMEOUT_S) as client:
            resp = client.post(CORE_CHECK_ENDPOINT, json=payload, headers=headers)
        elapsed = (datetime.now() - start).total_seconds() * 1000

        if elapsed > SLA_WARN_MS:
            logger.warning("Core response %.0fms — vượt SLA %dms", elapsed, SLA_WARN_MS)

        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                "Core OK: card=%s gate=%s result=%s reason=%s (%.0fms)",
                card_id, gate_id, data.get("result"), data.get("reasonCode"), elapsed,
            )
            return {
                "result": data.get("result", "DENY"),
                "reasonCode": data.get("reasonCode", "NO_REASON"),
                "decisionId": data.get("decisionId"),
                "policyId": data.get("policyId"),
                "evaluatedAt": data.get("evaluatedAt"),
                "source": "CORE",
            }

        # Các status code lỗi — fail-closed
        logger.warning(
            "Core trả %s cho card=%s gate=%s — fail-closed DENY",
            resp.status_code, card_id, gate_id,
        )
        return _deny(f"CORE_HTTP_{resp.status_code}")

    except httpx.TimeoutException:
        logger.warning("Core timeout (>%.1fs) card=%s gate=%s — fail-closed DENY",
                       CORE_TIMEOUT_S, card_id, gate_id)
        return _deny("CORE_TIMEOUT")
    except httpx.RequestError as e:
        logger.warning("Core không kết nối được — fail-closed DENY: %s", e)
        return _deny("CORE_UNREACHABLE")
    except Exception as e:
        logger.error("Lỗi không xác định khi gọi Core — fail-closed DENY: %s", e)
        return _deny("CORE_UNKNOWN_ERROR")


# ============================================================
# ANALYTICS EVENT PUBLISHER (Pair 09 — Quỳnh Đinh Trọng)
# Best-effort: gửi event sang broker MQTT Analytics
# ============================================================
def hash_card_id(card_id: str) -> str:
    digest = hashlib.sha256(card_id.encode()).hexdigest()
    return f"sha256:{digest}"


def publish_analytics_event(card_id: str, gate_id: str, direction: str, is_allowed: bool, reason_code: str):
    """
    Publish event theo đúng hợp đồng event-contract-template.md:
      - Granted: access.log.created
      - Denied: access.denied
    Không chặn luồng chính nếu lỗi mạng / broker chưa bật.
    """
    if not ENABLE_ANALYTICS_MQTT or mqtt_client is None:
        return

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if is_allowed:
        event_type = "access.log.created"
        data = {
            "gate_id": gate_id,
            "direction": direction.upper(),
            "card_id_hash": hash_card_id(card_id),
            "user_type": "student",
            "recorded_at": now_iso,
        }
    else:
        event_type = "access.denied"
        data = {
            "gate_id": gate_id,
            "card_id_hash": hash_card_id(card_id),
            "user_type": "student",
            "deny_reason": reason_code,
            "recorded_at": now_iso,
        }

    envelope = {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "occurredAt": now_iso,
        "correlationId": str(uuid.uuid4()),
        "source": "access-gate",
        "data": data,
    }

    try:
        c = mqtt_client.Client(client_id=f"gate-rest-{uuid.uuid4().hex[:6]}")
        c.connect(ANALYTICS_MQTT_HOST, ANALYTICS_MQTT_PORT, keepalive=10)
        c.publish(ANALYTICS_MQTT_TOPIC, json.dumps(envelope), qos=1)
        c.disconnect()
        logger.info("Published sang Analytics MQTT: %s (eventId=%s)", event_type, envelope["eventId"])
    except Exception as exc:
        logger.warning("Không thể publish sang Analytics MQTT (best-effort): %s", exc)


# ============================================================
# HIVEMQ LISTENER — NHẬN UID TỰ ĐỘNG TỪ MÁY THẦY (24/7)
# ============================================================
def load_whitelist() -> dict:
    """Đọc file Acessgate_uid_whitelist.csv của thầy, trả về dict {uid: info}."""
    whitelist = {}
    if not os.path.exists(WHITELIST_PATH):
        logger.warning("Không tìm thấy whitelist tại %s", WHITELIST_PATH)
        return whitelist

    try:
        with open(WHITELIST_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row.get("uid", "").strip()
                if uid:
                    whitelist[uid] = {
                        "student_id": row.get("student_id", "").strip(),
                        "full_name": row.get("full_name", "").strip(),
                        "class_name": row.get("class_name", "").strip(),
                    }
        logger.info("Đã load %d UID từ whitelist của Thầy", len(whitelist))
    except Exception as exc:
        logger.error("Lỗi đọc file whitelist: %s", exc)
    return whitelist


def start_hivemq_listener():
    """Chạy thread lắng nghe HiveMQ Cloud từ Pi RFID Simulator của thầy."""
    if not ENABLE_HIVEMQ or mqtt_client is None:
        logger.info("HiveMQ Listener bị tắt hoặc thiếu thư viện paho-mqtt")
        return

    whitelist = load_whitelist()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        logger.info("Kết nối HiveMQ Cloud của Thầy THÀNH CÔNG: %s", reason_code)
        client.subscribe(HIVEMQ_INPUT_TOPIC, qos=1)
        logger.info("Đã subscribe topic của Thầy: %s", HIVEMQ_INPUT_TOPIC)

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            uid = payload.get("uid")
            door_id = payload.get("door_id", "GATE-01")
            direction = payload.get("direction", "IN").upper()
            raw_event_id = payload.get("event_id", "")

            if not uid:
                return

            entry = whitelist.get(uid)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            log_id = str(uuid.uuid4())

            # Xử lý theo logic mục 6 của Thầy
            if entry:
                access_result = "granted"
                reason = "uid_matched"
                result_db = "ALLOW"
                reason_code_db = "VALID_CARD"
                student_id = entry["student_id"]
                full_name = entry["full_name"]
                class_name = entry["class_name"]
                gate_state = "OPEN"
            else:
                access_result = "denied"
                reason = "uid_not_found"
                result_db = "DENY"
                reason_code_db = "UNKNOWN_CARD"
                student_id = None
                full_name = None
                class_name = None
                gate_state = "CLOSED"

            logger.info("HiveMQ Event: UID=%s -> %s (%s) Door=%s", uid, access_result, reason, door_id)

            # 1. Ghi log thật vào PostgreSQL để Web UI và Core Business xem được
            try:
                gate_code = door_id.upper()
                if not GATE_ID_RE.match(gate_code):
                    gate_code = "GATE-01"

                with engine.connect() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO access_logs (log_id, card_id, gate_id, direction, result, reason_code, decision_id, operator_note, ts)
                            VALUES (:log_id, :card_id, :gate_id, :direction, :result, :reason_code, :decision_id, :note, now())
                        """),
                        {
                            "log_id": log_id,
                            "card_id": uid,
                            "gate_id": gate_code,
                            "direction": direction,
                            "result": result_db,
                            "reason_code": reason_code_db,
                            "decision_id": f"hivemq-{raw_event_id}",
                            "note": f"{full_name} ({student_id})" if full_name else "Thẻ lạ ngoài danh sách",
                        },
                    )
                    conn.execute(
                        text("""
                            INSERT INTO gates (gate_id, state, last_card_id, updated_at)
                            VALUES (:gate_id, :state, :card_id, now())
                            ON CONFLICT (gate_id) DO UPDATE
                            SET state = EXCLUDED.state, last_card_id = EXCLUDED.last_card_id, updated_at = now()
                        """),
                        {"gate_id": gate_code, "state": gate_state, "card_id": uid},
                    )
                    conn.commit()
            except Exception as e:
                logger.warning("Lỗi ghi log từ HiveMQ vào DB: %s", e)

            # 2. Publish kết quả sang output topic theo đúng định dạng mục 7 của Thầy
            output_payload = {
                "event_id": f"access-event-{uuid.uuid4().hex[:8]}",
                "event_type": "access.swipe.processed",
                "source_service": "team-gate",
                "timestamp": now_iso,
                "raw_event_id": raw_event_id,
                "uid": uid,
                "student_id": student_id,
                "full_name": full_name,
                "class_name": class_name,
                "door_id": door_id,
                "location": payload.get("location", "Main Gate"),
                "direction": direction.lower(),
                "access_result": access_result,
                "reason": reason,
            }
            client.publish(HIVEMQ_OUTPUT_TOPIC, json.dumps(output_payload), qos=1)

            # 3. Publish sang Analytics Service (Pair 09)
            publish_analytics_event(
                card_id=uid,
                gate_id=gate_code,
                direction=direction,
                is_allowed=(access_result == "granted"),
                reason_code=reason_code_db,
            )

        except Exception as exc:
            logger.error("Lỗi xử lý message HiveMQ: %s", exc)

    try:
        client = mqtt_client.Client(protocol=mqtt_client.MQTTv5)
        client.username_pw_set(HIVEMQ_USERNAME, HIVEMQ_PASSWORD)
        client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
        client.on_connect = on_connect
        client.on_message = on_message

        logger.info("Bắt đầu kết nối HiveMQ Cloud của Thầy (%s:%d)...", HIVEMQ_HOST, HIVEMQ_PORT)
        client.connect(HIVEMQ_HOST, HIVEMQ_PORT, keepalive=30)
        client.loop_forever()
    except Exception as exc:
        logger.error("Không thể duy trì kết nối HiveMQ: %s", exc)


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title="Smart Campus — Access Gate Service API",
    version="1.0.0",
    description=(
        "Access Gate Service nhận sự kiện quẹt thẻ RFID, "
        "kiểm tra quyền ra/vào qua Core Business, ghi log "
        "và cung cấp dữ liệu audit cho các service khác."
    ),
)


@app.on_event("startup")
def on_startup():
    wait_for_db_and_init()
    # Khởi chạy thread lắng nghe HiveMQ của Thầy chạy ngầm tự động 24/7
    if ENABLE_HIVEMQ:
        t = threading.Thread(target=start_hivemq_listener, daemon=True, name="HiveMQ-Listener")
        t.start()
        logger.info("Đã khởi chạy background thread lắng nghe HiveMQ Cloud của Thầy!")


# ============================================================
# ERROR HANDLER — RFC 7807 Problem Details
# ============================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(p) for p in e["loc"] if p not in ("query", "body", "path")),
            "code": e["type"].upper(),
            "message": e["msg"],
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        media_type="application/problem+json",
        content={
            "type": "https://campus.local/errors/validation",
            "title": "Dữ liệu không hợp lệ",
            "status": 422,
            "detail": "Tham số request không hợp lệ",
            "instance": str(request.url),
            "errors": errors,
        },
    )


_PROBLEM_SLUG = {
    400: "validation",
    401: "unauthorized",
    404: "not-found",
    409: "conflict",
    422: "business-rule",
    500: "internal",
}


def problem(code: int, title: str, detail: str, instance: str, errors=None):
    slug = _PROBLEM_SLUG.get(code, "error")
    return JSONResponse(
        status_code=code,
        media_type="application/problem+json",
        content={
            "type": f"https://campus.local/errors/{slug}",
            "title": title,
            "status": code,
            "detail": detail,
            "instance": instance,
            "errors": errors or [],
        },
    )


def check_auth(authorization: Optional[str], instance: str):
    if not authorization or not authorization.startswith("Bearer "):
        return problem(401, "Chưa xác thực", "Thiếu Bearer token", instance)
    if authorization.split(" ", 1)[1] != API_TOKEN:
        return problem(401, "Chưa xác thực", "Bearer token không hợp lệ", instance)
    return None


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================
class SwipeRequest(BaseModel):
    """Body cho POST /access/swipe"""
    cardId: str
    gateId: str
    direction: Literal["IN", "OUT"]

    @field_validator("cardId")
    @classmethod
    def val_card(cls, v):
        if not CARD_ID_RE.match(v):
            raise ValueError("cardId phải có dạng RFID-YYYY-NNN")
        return v

    @field_validator("gateId")
    @classmethod
    def val_gate(cls, v):
        if not GATE_ID_RE.match(v):
            raise ValueError("gateId phải có dạng GATE-NN")
        return v


class StudentCardRequest(BaseModel):
    cardType: Literal["STUDENT"]
    cardId: str
    personId: str
    studentCode: str

    @field_validator("cardId")
    @classmethod
    def val_card(cls, v):
        if not CARD_ID_RE.match(v):
            raise ValueError("cardId phải có dạng RFID-YYYY-NNN")
        return v


class StaffCardRequest(BaseModel):
    cardType: Literal["STAFF"]
    cardId: str
    personId: str
    department: str

    @field_validator("cardId")
    @classmethod
    def val_card(cls, v):
        if not CARD_ID_RE.match(v):
            raise ValueError("cardId phải có dạng RFID-YYYY-NNN")
        return v


# ============================================================
# ROW MAPPERS
# ============================================================
def _fmt(dt) -> Optional[str]:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def row_to_log(row) -> dict:
    return {
        "logId":        str(row.log_id),
        "cardId":       row.card_id,
        "gateId":       row.gate_id,
        "direction":    row.direction,
        "status":       "GRANTED" if row.result == "ALLOW" else "DENIED",
        "reasonCode":   row.reason_code,
        "decisionId":   row.decision_id,
        "operatorNote": row.operator_note,
        "timestamp":    _fmt(row.ts),
    }


def row_to_gate(row) -> dict:
    return {
        "gateId":     row.gate_id,
        "state":      row.state,
        "lastCardId": row.last_card_id,
        "updatedAt":  _fmt(row.updated_at),
    }


def row_to_card(row) -> dict:
    return {
        "cardId":    row.card_id,
        "personId":  row.person_id,
        "cardType":  row.card_type,
        "status":    row.status,
        "issuedAt":  _fmt(row.issued_at),
        "expiresAt": _fmt(row.expires_at),
    }


# ============================================================
# ENDPOINTS
# ============================================================

# ------ UI DASHBOARD ------
STATIC_INDEX_PATH = os.path.join(os.path.dirname(__file__), "static", "index.html")

@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Giao diện mô phỏng quẹt thẻ và giám sát trạng thái Access Gate."""
    if os.path.exists(STATIC_INDEX_PATH):
        return FileResponse(STATIC_INDEX_PATH)
    return {"message": "Access Gate Service is running. Visit /docs for Swagger API."}


# ------ HEALTH ------
@app.get("/health", tags=["health"])
def get_health():
    return {
        "status":  "ok",
        "service": APP_NAME,
        "time":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ------ SWIPE — Endpoint chính ------
@app.post("/access/swipe", tags=["access"])
def swipe_card(
    body: SwipeRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """
    Nhận sự kiện quẹt thẻ tại cổng:
      1. Kiểm tra auth
      2. Gọi Core Business POST /access/check để kiểm tra chính sách
      3. Ghi log ra/vào vào DB
      4. Cập nhật trạng thái cổng
      5. Trả kết quả ALLOW / DENY cho client

    Fail-closed: nếu Core timeout hoặc lỗi → DENY (không mở cổng).
    """
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    # 1. Gọi Core Business
    core = call_core_check(body.cardId, body.gateId, body.direction)
    access_granted = core["result"] == "ALLOW"

    log_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Ghi log + cập nhật gate trong cùng 1 transaction
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO access_logs
                    (log_id, card_id, gate_id, direction, result, reason_code, decision_id, ts)
                VALUES
                    (:log_id, :card_id, :gate_id, :direction, :result, :reason_code, :decision_id, now())
            """),
            {
                "log_id":      log_id,
                "card_id":     body.cardId,
                "gate_id":     body.gateId,
                "direction":   body.direction,
                "result":      "ALLOW" if access_granted else "DENY",
                "reason_code": core["reasonCode"],
                "decision_id": core.get("decisionId"),
            },
        )

        # Cập nhật trạng thái cổng
        conn.execute(
            text("""
                INSERT INTO gates (gate_id, state, last_card_id, updated_at)
                VALUES (:gate_id, :state, :card_id, now())
                ON CONFLICT (gate_id) DO UPDATE
                    SET state        = EXCLUDED.state,
                        last_card_id = EXCLUDED.last_card_id,
                        updated_at   = EXCLUDED.updated_at
            """),
            {
                "gate_id": body.gateId,
                "state":   "OPEN" if access_granted else "CLOSED",
                "card_id": body.cardId,
            },
        )
        conn.commit()

    logger.info(
        "SWIPE card=%s gate=%s direction=%s → %s (%s) source=%s",
        body.cardId, body.gateId, body.direction,
        core["result"], core["reasonCode"], core["source"],
    )

    # 3. Publish sang Analytics Service (Pair 09 — Quỳnh Đinh Trọng)
    publish_analytics_event(
        card_id=body.cardId,
        gate_id=body.gateId,
        direction=body.direction,
        is_allowed=access_granted,
        reason_code=core["reasonCode"],
    )

    return {
        "logId":          log_id,
        "cardId":         body.cardId,
        "gateId":         body.gateId,
        "direction":      body.direction,
        "accessGranted":  access_granted,
        "result":         core["result"],
        "reasonCode":     core["reasonCode"],
        "decisionId":     core.get("decisionId"),
        "policyId":       core.get("policyId"),
        "decisionSource": core["source"],
        "timestamp":      now_str,
    }


# ------ ACCESS LOGS ------
@app.get("/access/logs/recent", tags=["access-logs"])
def list_recent_logs(
    request: Request,
    cursor:    Optional[str] = Query(default=None),
    limit:     int           = Query(default=20, ge=1, le=100),
    gateId:    Optional[str] = Query(default=None),
    startTime: Optional[str] = Query(default=None, description="ISO 8601, ví dụ 2026-08-11T00:00:00Z"),
    endTime:   Optional[str] = Query(default=None, description="ISO 8601, ví dụ 2026-08-11T23:59:59Z"),
    authorization: Optional[str] = Header(default=None),
):
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    if gateId and not GATE_ID_RE.match(gateId):
        return problem(400, "Dữ liệu không hợp lệ", "gateId sai định dạng", str(request.url),
                       [{"field": "gateId", "code": "PATTERN_MISMATCH",
                         "message": "gateId phải có dạng GATE-NN"}])

    # Build query động
    conditions = []
    params: dict = {"limit": limit}

    if gateId:
        conditions.append("gate_id = :gate_id")
        params["gate_id"] = gateId
    if startTime:
        conditions.append("ts >= :start_time")
        params["start_time"] = startTime
    if endTime:
        conditions.append("ts <= :end_time")
        params["end_time"] = endTime

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM access_logs {where} ORDER BY ts DESC LIMIT :limit"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    return {"items": [row_to_log(r) for r in rows], "nextCursor": None, "hasMore": False}


@app.get("/access/logs/{logId}", tags=["access-logs"])
def get_log_by_id(
    request: Request,
    logId: str = Path(...),
    authorization: Optional[str] = Header(default=None),
):
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM access_logs WHERE log_id = :id"), {"id": logId}
        ).fetchone()

    if not row:
        return problem(404, "Không tìm thấy", "logId không tồn tại", str(request.url))
    return row_to_log(row)


# ------ GATES ------
@app.get("/gates/{gateId}/status", tags=["gates"])
def get_gate_status(
    request: Request,
    gateId: str = Path(...),
    authorization: Optional[str] = Header(default=None),
):
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    if not GATE_ID_RE.match(gateId):
        return problem(400, "Dữ liệu không hợp lệ", "gateId sai định dạng", str(request.url),
                       [{"field": "gateId", "code": "PATTERN_MISMATCH",
                         "message": "gateId phải có dạng GATE-NN"}])

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM gates WHERE gate_id = :id"), {"id": gateId}
        ).fetchone()

    if not row:
        return problem(404, "Không tìm thấy", "gateId không tồn tại", str(request.url))
    return row_to_gate(row)


# ------ CARDS ------
@app.get("/cards/{cardId}", tags=["cards"])
def get_card_by_id(
    request: Request,
    cardId: str = Path(...),
    authorization: Optional[str] = Header(default=None),
):
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    if not CARD_ID_RE.match(cardId):
        return problem(400, "Dữ liệu không hợp lệ", "cardId sai định dạng", str(request.url),
                       [{"field": "cardId", "code": "PATTERN_MISMATCH",
                         "message": "cardId phải có dạng RFID-YYYY-NNN"}])

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM cards WHERE card_id = :id"), {"id": cardId}
        ).fetchone()

    if not row:
        return problem(404, "Không tìm thấy", "cardId không tồn tại", str(request.url))
    return row_to_card(row)


@app.post("/cards", status_code=status.HTTP_201_CREATED, tags=["cards"])
async def register_card(
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return problem(400, "Dữ liệu không hợp lệ", "Payload không đúng JSON", str(request.url))

    card_type = body.get("cardType")
    instance  = str(request.url)

    if card_type not in ("STUDENT", "STAFF"):
        return problem(400, "Dữ liệu không hợp lệ", "cardType phải là STUDENT hoặc STAFF",
                       instance, [{"field": "cardType", "code": "INVALID_VALUE",
                                   "message": "Chỉ chấp nhận STUDENT hoặc STAFF"}])
    try:
        parsed = StudentCardRequest(**body) if card_type == "STUDENT" else StaffCardRequest(**body)
    except Exception as exc:
        return problem(400, "Dữ liệu không hợp lệ", "Payload sai schema", instance,
                       [{"field": "cardId", "code": "PATTERN_MISMATCH", "message": str(exc)}])

    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM cards WHERE card_id = :id"), {"id": parsed.cardId}
        ).fetchone()
        if exists:
            return problem(409, "Thẻ đã tồn tại", "cardId đã được đăng ký", instance)

        conn.execute(
            text("""
                INSERT INTO cards (card_id, person_id, card_type, status, issued_at)
                VALUES (:card_id, :person_id, :card_type, 'ACTIVE', now())
            """),
            {"card_id": parsed.cardId, "person_id": parsed.personId, "card_type": parsed.cardType},
        )
        conn.commit()
        row = conn.execute(
            text("SELECT * FROM cards WHERE card_id = :id"), {"id": parsed.cardId}
        ).fetchone()

    logger.info("Đăng ký thẻ mới: %s (%s) → %s", parsed.cardId, parsed.cardType, parsed.personId)
    return row_to_card(row)
