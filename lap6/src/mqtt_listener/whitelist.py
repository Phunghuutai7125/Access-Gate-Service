"""
whitelist.py - Doc uid_whitelist.csv, khong hardcode UID trong logic chinh.
Theo dung yeu cau muc 5: "Co the load file khi service khoi dong."
"""
import csv
import logging
import os

logger = logging.getLogger("mqtt_listener.whitelist")

WHITELIST_PATH = os.getenv("UID_WHITELIST_PATH", "data/uid_whitelist.csv")


def load_whitelist(path: str = WHITELIST_PATH) -> dict:
    """Doc file CSV, tra ve dict {uid: {student_id, full_name, class_name}}."""
    whitelist = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            whitelist[row["uid"].strip()] = {
                "student_id": row["student_id"].strip(),
                "full_name": row["full_name"].strip(),
                "class_name": row["class_name"].strip(),
            }
    logger.info("Da load %d UID tu whitelist: %s", len(whitelist), path)
    return whitelist
