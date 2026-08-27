"""Script test rieng - chi test ket noi MQTT, KHONG dung DB.
Chay: python test_mqtt_only.py
"""
import os
import ssl
import json
import logging

from paho.mqtt import client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mqtt_test")

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
INPUT_TOPIC = os.getenv("MQTT_INPUT_TOPIC", "smart-campus/raw/access/rfid-uid")


def on_connect(client, userdata, flags, reason_code, properties=None):
    logger.info("Ket noi: %s", reason_code)
    client.subscribe(INPUT_TOPIC, qos=1)
    logger.info("Da subscribe: %s", INPUT_TOPIC)


def on_message(client, userdata, message):
    logger.info("NHAN DUOC EVENT: %s", message.payload.decode())


client = mqtt.Client(protocol=mqtt.MQTTv5)
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_HOST, MQTT_PORT)
client.loop_forever()
