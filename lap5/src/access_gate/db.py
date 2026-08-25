"""
db.py - Ket noi Postgres that cho Access Gate Service (Lab05).
Dung SQLAlchemy Core (khong ORM) de giu don gian, de doc.
"""
import os
import time
import logging
from sqlalchemy import create_engine, text

logger = logging.getLogger("access_gate.db")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "access_gate_db")
DB_USER = os.getenv("DB_USER", "access_gate_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cards (
    card_id     VARCHAR(20) PRIMARY KEY,
    person_id   VARCHAR(50) NOT NULL,
    card_type   VARCHAR(10) NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS gates (
    gate_id     VARCHAR(10) PRIMARY KEY,
    state       VARCHAR(10) NOT NULL,
    last_card_id VARCHAR(20),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS access_logs (
    log_id      UUID PRIMARY KEY,
    card_id     VARCHAR(20) NOT NULL,
    gate_id     VARCHAR(10) NOT NULL,
    direction   VARCHAR(5) NOT NULL,
    status      VARCHAR(10) NOT NULL,
    reason_code VARCHAR(30),
    operator_note TEXT,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

SEED_SQL = """
INSERT INTO cards (card_id, person_id, card_type, status, issued_at)
VALUES ('RFID-9215-649', 'SV001', 'STUDENT', 'ACTIVE', '2026-01-10T00:00:00Z')
ON CONFLICT (card_id) DO NOTHING;

INSERT INTO gates (gate_id, state, last_card_id, updated_at)
VALUES ('GATE-79', 'OPEN', 'RFID-9215-649', '2026-08-11T07:30:00Z')
ON CONFLICT (gate_id) DO NOTHING;

INSERT INTO access_logs (log_id, card_id, gate_id, direction, status, reason_code, ts)
VALUES ('3d906e18-c3d6-f4f7-edc7-b1a59761d251', 'RFID-9215-649', 'GATE-79', 'IN', 'GRANTED', 'VALID_CARD', '2026-08-11T07:30:00Z')
ON CONFLICT (log_id) DO NOTHING;
"""


def wait_for_db_and_init(max_retries: int = 15, delay_seconds: float = 2.0):
    """Retry ket noi DB luc startup - phong truong hop container db chua kip san sang
    du da co healthcheck/depends_on (thuc hanh chuyen nghiep, khong tin tuong 100% vao thu tu Compose)."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.execute(text(SCHEMA_SQL))
                conn.execute(text(SEED_SQL))
                conn.commit()
            logger.info("Ket noi Postgres thanh cong sau %d lan thu", attempt)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("DB chua san sang (lan %d/%d): %s", attempt, max_retries, exc)
            time.sleep(delay_seconds)
    raise RuntimeError(f"Khong ket noi duoc Postgres sau {max_retries} lan thu: {last_error}")
