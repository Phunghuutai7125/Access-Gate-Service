"""
Access Gate Service - FIT4110 Lab04
Implement theo contracts/team-gate.openapi.yaml (Lab03).
"""
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal

from fastapi import FastAPI, Request, Header, Query, Path, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

APP_NAME = "access-gate-service"
API_TOKEN = os.getenv("ACCESS_GATE_API_TOKEN", "dev-secret-token")

GATE_ID_RE = re.compile(r"^GATE-[0-9]{2}$")
CARD_ID_RE = re.compile(r"^RFID-[0-9]{4}-[0-9]{3}$")

app = FastAPI(title="Smart Campus - Access Gate Service API", version="1.0.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Chuyển lỗi validate query/path param (vd limit>100) sang chuẩn ProblemDetails."""
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

# ---------------------------------------------------------------------------
# In-memory data (đủ để Newman test chạy pass; thay bằng DB thật nếu cần)
# Seed khớp với ID mẫu trong postman/collections/team-gate.postman_collection.json
# (RFID-9215-649, GATE-79, 3d906e18-...) để test happy-path trả 200/201 đúng.
# KHÔNG seed RFID-2026-001 vì đó là body của test "Đăng ký thẻ mới" (cần trả 201).
# ---------------------------------------------------------------------------
ACCESS_LOGS = [
    {
        "logId": "3d906e18-c3d6-f4f7-edc7-b1a59761d251",
        "cardId": "RFID-9215-649",
        "gateId": "GATE-79",
        "direction": "IN",
        "status": "GRANTED",
        "reasonCode": "VALID_CARD",
        "operatorNote": None,
        "timestamp": "2026-08-11T07:30:00Z",
    }
]

GATES = {
    "GATE-79": {
        "gateId": "GATE-79",
        "state": "OPEN",
        "lastCardId": "RFID-9215-649",
        "updatedAt": "2026-08-11T07:30:00Z",
    }
}

CARDS = {
    "RFID-9215-649": {
        "cardId": "RFID-9215-649",
        "personId": "SV001",
        "cardType": "STUDENT",
        "status": "ACTIVE",
        "issuedAt": "2026-01-10T00:00:00Z",
        "expiresAt": None,
    }
}


# ---------------------------------------------------------------------------
# Problem Details helper (RFC 7807)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
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

    items = ACCESS_LOGS
    if gateId:
        if not GATE_ID_RE.match(gateId):
            return problem(400, "Dữ liệu không hợp lệ", "gateId sai định dạng", str(request.url),
                            [{"field": "gateId", "code": "PATTERN_MISMATCH", "message": "gateId phải có dạng GATE-NN"}])
        items = [log for log in items if log["gateId"] == gateId]

    page = items[:limit]
    return {"items": page, "nextCursor": None, "hasMore": False}


@app.get("/access/logs/{logId}")
def get_access_log_by_id(
    request: Request,
    logId: str = Path(...),
    authorization: Optional[str] = Header(default=None),
):
    err = check_auth(authorization, str(request.url))
    if err:
        return err

    for log in ACCESS_LOGS:
        if log["logId"] == logId:
            return log
    return problem(404, "Không tìm thấy tài nguyên", "logId không tồn tại trong hệ thống", str(request.url))


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

    gate = GATES.get(gateId)
    if not gate:
        return problem(404, "Không tìm thấy tài nguyên", "gateId không tồn tại trong hệ thống", str(request.url))
    return gate


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

    card = CARDS.get(cardId)
    if not card:
        return problem(404, "Không tìm thấy tài nguyên", "cardId không tồn tại trong hệ thống", str(request.url))
    return card


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

    if parsed.cardId in CARDS:
        return problem(409, "Thẻ đã tồn tại", "cardId đã được đăng ký trước đó", instance)

    new_card = {
        "cardId": parsed.cardId,
        "personId": parsed.personId,
        "cardType": parsed.cardType,
        "status": "ACTIVE",
        "issuedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expiresAt": None,
    }
    CARDS[parsed.cardId] = new_card
    return new_card
