"""
Access Gate Service - FIT4110 Lab05
Ket noi Postgres that (xem db.py). Giu nguyen contract team-gate.openapi.yaml.
"""
import os
import re
import logging
from datetime import datetime, timezone
from typing import Optional, Literal

import httpx
from fastapi import FastAPI, Request, Header, Query, Path, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import text

from src.access_gate.db import engine, wait_for_db_and_init

logger = logging.getLogger("access_gate")

APP_NAME = "access-gate-service"
API_TOKEN = os.getenv("ACCESS_GATE_API_TOKEN", "dev-secret-token")
GATE_WORKER_URL = os.getenv("GATE_WORKER_URL", "http://gate-worker:9000")

GATE_ID_RE = re.compile(r"^GATE-[0-9]{2}$")
CARD_ID_RE = re.compile(r"^RFID-[0-9]{4}-[0-9]{3}$")

app = FastAPI(title="Smart Campus - Access Gate Service API", version="1.0.0")


@app.on_event("startup")
def on_startup():
    """Ket noi Postgres that, tao schema + seed data khop voi Postman collection."""
    wait_for_db_and_init()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    field_errors = [
        {
            "field": ".".join(str(p) for p in err["loc"] if p != "query"),
            "code": err["type"].upper(),
            "message": err["msg"],
        }
        for err in exc.errors()
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
            "errors": field_errors,
        },
    )


PROBLEM_TYPE_SLUGS = {
    400: "validation",
    401: "unauthorized",
    404: "not-found",
    409: "conflict",
    422: "business-rule",
    500: "internal",
}


def problem(status_code: int, title: str, detail: str, instance: str, errors=None):
    slug = PROBLEM_TYPE_SLUGS.get(status_code, "error")
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": f"https://campus.local/errors/{slug}",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
            "errors": errors or [],
        },
    )


def check_auth(authorization: Optional[str], instance: str):
    if not authorization or not authorization.startswith("Bearer "):
        return problem(401, "Chưa xác thực", "Thiếu Bearer token", instance)
    token = authorization.split(" ", 1)[1]
    if token != API_TOKEN:
        return problem(401, "Chưa xác thực", "Bearer token không hợp lệ", instance)
    return None


class StudentCardRequest(BaseModel):
    cardType: Literal["STUDENT"]
    cardId: str
    personId: str
    studentCode: str

    @field_validator("cardId")
    @classmethod
    def validate_card_id(cls, v):
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
    def validate_card_id(cls, v):
        if not CARD_ID_RE.match(v):
            raise ValueError("cardId phải có dạng RFID-YYYY-NNN")
        return v


def row_to_card(row) -> dict:
    return {
        "cardId": row.card_id,
        "personId": row.person_id,
        "cardType": row.card_type,
        "status": row.status,
        "issuedAt": row.issued_at.strftime("%Y-%m-%dT%H:%M:%SZ") if row.issued_at else None,
        "expiresAt": row.expires_at.strftime("%Y-%m-%dT%H:%M:%SZ") if row.expires_at else None,
    }


def row_to_gate(row) -> dict:
    return {
        "gateId": row.gate_id,
        "state": row.state,
        "lastCardId": row.last_card_id,
        "updatedAt": row.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if row.updated_at else None,
    }


def row_to_log(row) -> dict:
    return {
        "logId": str(row.log_id),
        "cardId": row.card_id,
        "gateId": row.gate_id,
        "direction": row.direction,
        "status": row.status,
        "reasonCode": row.reason_code,
        "operatorNote": row.operator_note,
        "timestamp": row.ts.strftime("%Y-%m-%dT%H:%M:%SZ") if row.ts else None,
    }


async def notify_gate_worker(event: dict):
    """Gui async event sang gate-worker (thay AI, dong vai Analytics - pair-09).
    Khong chan response chinh neu worker loi/cham - chi log canh bao."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(f"{GATE_WORKER_URL}/events/access", json=event)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Khong gui duoc event sang gate-worker: %s", exc)


@app.get("/health")
def get_health():
    return {
        "status": "ok",
        "service": APP_NAME,
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/access/logs/recent")
def list_recent_access_logs(
    request: Request,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    gateId: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
):
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    if gateId and not GATE_ID_RE.match(gateId):
        return problem(400, "Dữ liệu không hợp lệ", "gateId sai định dạng", str(request.url),
                        [{"field": "gateId", "code": "PATTERN_MISMATCH", "message": "gateId phải có dạng GATE-NN"}])

    sql = "SELECT * FROM access_logs"
    params = {"limit": limit}
    if gateId:
        sql += " WHERE gate_id = :gate_id"
        params["gate_id"] = gateId
    sql += " ORDER BY ts DESC LIMIT :limit"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    return {"items": [row_to_log(r) for r in rows], "nextCursor": None, "hasMore": False}


@app.get("/access/logs/{logId}")
def get_access_log_by_id(
    request: Request,
    logId: str = Path(...),
    authorization: Optional[str] = Header(default=None),
):
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM access_logs WHERE log_id = :id"), {"id": logId}).fetchone()

    if not row:
        return problem(404, "Không tìm thấy tài nguyên", "logId không tồn tại trong hệ thống", str(request.url))
    return row_to_log(row)


@app.get("/gates/{gateId}/status")
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
                        [{"field": "gateId", "code": "PATTERN_MISMATCH", "message": "gateId phải có dạng GATE-NN"}])

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM gates WHERE gate_id = :id"), {"id": gateId}).fetchone()

    if not row:
        return problem(404, "Không tìm thấy tài nguyên", "gateId không tồn tại trong hệ thống", str(request.url))
    return row_to_gate(row)


@app.get("/cards/{cardId}")
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
                        [{"field": "cardId", "code": "PATTERN_MISMATCH", "message": "cardId phải có dạng RFID-YYYY-NNN"}])

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM cards WHERE card_id = :id"), {"id": cardId}).fetchone()

    if not row:
        return problem(404, "Không tìm thấy tài nguyên", "cardId không tồn tại trong hệ thống", str(request.url))
    return row_to_card(row)


@app.post("/cards", status_code=status.HTTP_201_CREATED)
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
        return problem(400, "Dữ liệu không hợp lệ", "Payload không đúng JSON Schema", str(request.url))

    card_type = body.get("cardType")
    instance = str(request.url)

    if card_type not in ("STUDENT", "STAFF"):
        return problem(400, "Dữ liệu không hợp lệ", "cardType phải là STUDENT hoặc STAFF", instance,
                        [{"field": "cardType", "code": "PATTERN_MISMATCH", "message": "cardType không hợp lệ"}])

    try:
        if card_type == "STUDENT":
            parsed = StudentCardRequest(**body)
        else:
            parsed = StaffCardRequest(**body)
    except Exception as exc:
        return problem(400, "Dữ liệu không hợp lệ", "Payload không đúng JSON Schema", instance,
                        [{"field": "cardId", "code": "PATTERN_MISMATCH", "message": str(exc)}])

    with engine.connect() as conn:
        existing = conn.execute(text("SELECT 1 FROM cards WHERE card_id = :id"), {"id": parsed.cardId}).fetchone()
        if existing:
            return problem(409, "Thẻ đã tồn tại", "cardId đã được đăng ký trước đó", instance)

        conn.execute(
            text("""
                INSERT INTO cards (card_id, person_id, card_type, status, issued_at)
                VALUES (:card_id, :person_id, :card_type, 'ACTIVE', now())
            """),
            {"card_id": parsed.cardId, "person_id": parsed.personId, "card_type": parsed.cardType},
        )
        conn.commit()

        row = conn.execute(text("SELECT * FROM cards WHERE card_id = :id"), {"id": parsed.cardId}).fetchone()

    new_card = row_to_card(row)

    await notify_gate_worker({"event": "CARD_REGISTERED", "cardId": new_card["cardId"], "cardType": new_card["cardType"]})

    return new_card
