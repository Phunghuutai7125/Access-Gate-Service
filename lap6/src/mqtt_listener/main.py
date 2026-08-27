"""
mqtt_listener - AccessGate Service (team-gate)
Nhan UID raw tu HiveMQ, doi chieu uid_whitelist.csv, publish ket qua xu ly.

Chay doc lap voi REST API (main.py trong access_gate) - day la them 1 service moi,
KHONG thay the REST API. REST API van phuc vu Pair-03 (Core Business goi vao).
mqtt_listener phu trach Pair-09 that (publish event that qua MQTT thay vi gate-worker gia lap).
"""
import os
import ssl
import json
import logging
import uuid
from datetime import datetime, timezone

from paho.mqtt import client as mqtt

from src.mqtt_listener.whitelist import load_whitelist

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mqtt_listener")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() == "true"

INPUT_TOPIC = os.getenv("MQTT_INPUT_TOPIC", "smart-campus/raw/access/rfid-uid")
OUTPUT_TOPIC = os.getenv("MQTT_OUTPUT_TOPIC", "smart-campus/events/access")
SOURCE_SERVICE = "team-gate"

REQUIRED_FIELDS = ["event_id", "event_type", "timestamp", "uid", "door_id", "direction"]

whitelist = load_whitelist()


def validate_payload(payload: dict) -> list:
    """Tra ve danh sach field bi thieu (rong neu hop le)."""
    return [f for f in REQUIRED_FIELDS if f not in payload or payload[f] in (None, "")]


def process_uid(payload: dict) -> dict:
    """Doi chieu uid voi whitelist, tra ve payload ket qua theo dung format muc 7."""
    uid = payload["uid"]
    entry = whitelist.get(uid)

    result = {
        "event_id": f"access-event-{uuid.uuid4().hex[:8]}",
        "event_type": "access.swipe.processed",
        "source_service": SOURCE_SERVICE,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "raw_event_id": payload["event_id"],
        "uid": uid,
        "door_id": payload["door_id"],
        "location": payload.get("location"),
        "direction": payload["direction"],
    }

    if entry:
        result.update({
            "student_id": entry["student_id"],
            "full_name": entry["full_name"],
            "class_name": entry["class_name"],
            "access_result": "granted",
            "reason": "uid_matched",
        })
    else:
        result.update({
            "student_id": None,
            "full_name": None,
            "class_name": None,
            "access_result": "denied",
            "reason": "uid_not_found",
        })
    return result


def on_connect(client, userdata, flags, reason_code, properties=None):
    logger.info("Ket noi MQTT: %s", reason_code)
    client.subscribe(INPUT_TOPIC, qos=1)
    logger.info("Da subscribe topic: %s", INPUT_TOPIC)


def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode())
    except json.JSONDecodeError:
        logger.warning("Payload khong phai JSON hop le, bo qua: %s", message.payload)
        return

    missing = validate_payload(payload)
    if missing:
        logger.warning("Payload thieu field bat buoc %s, bo qua: %s", missing, payload)
        return

    result = process_uid(payload)
    client.publish(OUTPUT_TOPIC, json.dumps(result), qos=1)
    logger.info(
        "UID=%s -> %s (%s) | door=%s | published to %s",
        result["uid"], result["access_result"], result["reason"], result["door_id"], OUTPUT_TOPIC,
    )


def build_client() -> mqtt.Client:
    client = mqtt.Client(protocol=mqtt.MQTTv5)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_USE_TLS:
        client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.on_connect = on_connect
    client.on_message = on_message
    return client


def main():
    client = build_client()
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_forever()


if __name__ == "__main__":
    main()
