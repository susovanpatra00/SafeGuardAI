"""
Shared message protocol between client and server.
Both sides import this so the message format never drifts out of sync.

Wire format over the websocket:
- Binary messages = raw JPEG-encoded frame bytes (video data)
- Text messages    = JSON control/metadata messages (see below)

This keeps video data lightweight (no base64 overhead) while still allowing
structured JSON for things like camera_id, alerts, and heartbeats.
"""

import json
import time

# ---- Message types (JSON, sent as text frames over the websocket) ----

MSG_HELLO = "hello"          # client -> server, sent once on connect
MSG_HEARTBEAT = "heartbeat"  # client -> server, periodic keep-alive
MSG_ALERT = "alert"          # server -> client, breach detected
MSG_ACK = "ack"              # server -> client, generic acknowledgement


def make_hello(camera_id: str, width: int, height: int, fps: int) -> str:
    """First message a client sends after connecting, identifying itself."""
    return json.dumps({
        "type": MSG_HELLO,
        "camera_id": camera_id,
        "width": width,
        "height": height,
        "fps": fps,
        "ts": time.time(),
    })


def make_heartbeat(camera_id: str) -> str:
    return json.dumps({
        "type": MSG_HEARTBEAT,
        "camera_id": camera_id,
        "ts": time.time(),
    })


def make_alert(camera_id: str, snapshot_path: str) -> str:
    return json.dumps({
        "type": MSG_ALERT,
        "camera_id": camera_id,
        "snapshot": snapshot_path,
        "ts": time.time(),
    })


def parse_message(raw: str) -> dict:
    """Parse an incoming JSON text message. Raises ValueError if malformed."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed message: {e}")
    if "type" not in data:
        raise ValueError("Message missing 'type' field")
    return data