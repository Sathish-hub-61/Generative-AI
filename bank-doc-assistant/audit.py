"""Append-only audit log."""
import json, time
from pathlib import Path

LOG_PATH = Path(__file__).parent / "audit_log.jsonl"

def log_event(event: str, payload: dict):
    rec = {"ts": time.time(), "event": event, "payload": payload}
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")