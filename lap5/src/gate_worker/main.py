"""
gate-worker - FIT4110 Lab05
team-gate KHONG dung AI service (theo phan cong de bai), thay bang worker
gia lap tiep nhan access event async gui sang Analytics (pair-09).
"""
from datetime import datetime, timezone
from fastapi import FastAPI, Request

app = FastAPI(title="Gate Worker - Async Event Receiver")

RECEIVED_EVENTS = []


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "gate-worker",
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.post("/events/access")
async def receive_access_event(request: Request):
    """Endpoint gia lap Analytics nhan async event tu Access Gate (pair-09)."""
    body = await request.json()
    RECEIVED_EVENTS.append(body)
    return {"received": True, "totalReceived": len(RECEIVED_EVENTS)}


@app.get("/events/access")
def list_received_events():
    return {"items": RECEIVED_EVENTS, "count": len(RECEIVED_EVENTS)}
