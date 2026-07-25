"""
Server: receives video frames from remote clients over WebSocket.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000

Each client connects to ws://SERVER_IP:8000/ws/stream
and must send:
    1. One JSON "hello" text message first (camera_id, width, height, fps)
    2. Then a continuous stream of binary messages, each one JPEG-encoded frame

Perimeter zones are set per-camera via REST (POST /zone/{camera_id}) since
the client has no notion of "where the zone is" -- that's a server-side
concept an operator configures once a camera is streaming.
"""

import sys
import os
import time
import logging

import numpy as np
import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Allow importing shared/protocol.py from the sibling "shared" folder
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from protocol import parse_message, MSG_HELLO, MSG_HEARTBEAT  # noqa: E402

from detector import PerimeterDetector
from auth import verify_key, verify_websocket_key, API_KEY  # noqa: F401 (API_KEY imported for startup log ordering)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("server")

app = FastAPI()

ALERTS_DIR = os.path.join(os.path.dirname(__file__), "alerts")
os.makedirs(ALERTS_DIR, exist_ok=True)

# Single shared detector instance -- the YOLO model is loaded once at startup
# and reused across all cameras/frames (loading it per-frame would be very slow).
detector = PerimeterDetector(frames_to_confirm=3, alert_cooldown_sec=5.0)


class CameraSession:
    """Tracks state for one connected camera client."""

    def __init__(self, camera_id: str, width: int, height: int, fps: int):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_count = 0
        self.alert_count = 0
        self.connected_at = time.time()
        self.last_frame_at = None
        self.latest_jpeg: bytes | None = None  # most recent raw frame, for the zone-drawing tool

    def register_frame(self, raw_jpeg: bytes):
        self.frame_count += 1
        self.last_frame_at = time.time()
        self.latest_jpeg = raw_jpeg


class ConnectionManager:
    """Keeps track of all active camera sessions, keyed by camera_id."""

    def __init__(self):
        self.sessions: dict[str, CameraSession] = {}

    def add(self, session: CameraSession):
        self.sessions[session.camera_id] = session
        log.info(f"Camera '{session.camera_id}' connected "
                 f"({session.width}x{session.height} @ {session.fps}fps)")

    def remove(self, camera_id: str):
        if camera_id in self.sessions:
            del self.sessions[camera_id]
            log.info(f"Camera '{camera_id}' disconnected")

    def status(self) -> dict:
        return {
            cam_id: {
                "frames_received": s.frame_count,
                "alerts_triggered": s.alert_count,
                "connected_at": s.connected_at,
                "last_frame_at": s.last_frame_at,
            }
            for cam_id, s in self.sessions.items()
        }


manager = ConnectionManager()


def decode_frame(raw_bytes: bytes) -> np.ndarray | None:
    """Decode JPEG bytes into an OpenCV BGR image. Returns None if corrupt."""
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame  # None if decode failed


def process_frame(camera_id: str, frame: np.ndarray, session: "CameraSession"):
    """
    Runs YOLO person detection + perimeter breach check on one frame.
    If a confirmed breach fires (post-debounce, post-cooldown), saves an
    annotated snapshot to alerts/ and logs it.
    """
    result = detector.process_frame(camera_id, frame)

    if result["breach"]["should_alert"]:
        session.alert_count += 1
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        snapshot = detector.draw_overlay(frame, camera_id, result)
        path = os.path.join(ALERTS_DIR, f"{camera_id}_{timestamp}.jpg")
        cv2.imwrite(path, snapshot)
        log.warning(f"[ALERT] '{camera_id}' perimeter breached -> saved {path}")
        # TODO: this is where you'd push a notification -- webhook, email,
        # Telegram, etc. -- in addition to the saved snapshot.


class ZoneRequest(BaseModel):
    points: list[list[int]]  # [[x1,y1], [x2,y2], ...] -- at least 3 points


@app.post("/zone/{camera_id}", dependencies=[Depends(verify_key)])
def set_zone(camera_id: str, zone: ZoneRequest):
    """Define/update the perimeter polygon for a camera."""
    if len(zone.points) < 3:
        raise HTTPException(status_code=400, detail="Zone needs at least 3 points")
    polygon = [(p[0], p[1]) for p in zone.points]
    detector.set_zone(camera_id, polygon)
    return {"camera_id": camera_id, "zone": polygon}


@app.get("/zone/{camera_id}", dependencies=[Depends(verify_key)])
def get_zone(camera_id: str):
    """Fetch the currently configured perimeter polygon for a camera."""
    zone = detector.get_zone(camera_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"No zone configured for '{camera_id}'")
    return {"camera_id": camera_id, "zone": zone}


@app.get("/status", dependencies=[Depends(verify_key)])
def get_status():
    """Simple REST endpoint to check which cameras are connected."""
    return manager.status()


@app.get("/snapshot/{camera_id}", dependencies=[Depends(verify_key)])
def get_snapshot(camera_id: str):
    """Returns the most recently received frame from a camera as a raw JPEG.
    Used by the zone-drawing tool to show a live reference image."""
    session = manager.sessions.get(camera_id)
    if session is None or session.latest_jpeg is None:
        raise HTTPException(status_code=404, detail=f"No frames received yet from '{camera_id}'")
    return Response(content=session.latest_jpeg, media_type="image/jpeg")


_ZONE_EDITOR_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "static", "zone_editor.html")


@app.get("/zone-editor/{camera_id}", response_class=HTMLResponse, dependencies=[Depends(verify_key)])
def zone_editor(camera_id: str, key: str):
    """
    Visual perimeter-drawing tool. Open this in a browser to see a live
    snapshot from the camera and click points directly on it to define
    the zone -- no manual coordinate entry needed.
    Requires ?key=... in the URL (same API key as everything else).
    """
    with open(_ZONE_EDITOR_TEMPLATE_PATH, "r") as f:
        html = f.read()
    html = html.replace("{{CAMERA_ID}}", camera_id).replace("{{API_KEY}}", key)
    return HTMLResponse(content=html)


@app.websocket("/ws/stream")
async def stream_endpoint(websocket: WebSocket):
    if not verify_websocket_key(websocket):
        # Must accept before we can close with a reason -- Starlette requires
        # the handshake to complete before sending a close frame.
        await websocket.accept()
        await websocket.close(code=4401, reason="Invalid or missing API key")
        log.warning(f"Rejected websocket connection from {websocket.client}: bad API key")
        return

    await websocket.accept()
    session: CameraSession | None = None

    try:
        while True:
            message = await websocket.receive()

            # Starlette sends this when the client closes the connection.
            # Must check for it explicitly, or the next receive() call raises.
            if message["type"] == "websocket.disconnect":
                break

            # Text message = JSON control message (hello / heartbeat)
            if "text" in message and message["text"] is not None:
                try:
                    data = parse_message(message["text"])
                except ValueError as e:
                    log.warning(f"Bad control message: {e}")
                    continue

                if data["type"] == MSG_HELLO:
                    session = CameraSession(
                        camera_id=data["camera_id"],
                        width=data.get("width", 0),
                        height=data.get("height", 0),
                        fps=data.get("fps", 0),
                    )
                    manager.add(session)

                elif data["type"] == MSG_HEARTBEAT:
                    if session:
                        log.debug(f"Heartbeat from '{session.camera_id}'")

            # Binary message = a JPEG frame
            elif "bytes" in message and message["bytes"] is not None:
                if session is None:
                    log.warning("Received frame before 'hello' message — ignoring")
                    continue

                frame = decode_frame(message["bytes"])
                if frame is None:
                    log.warning(f"Corrupt frame from '{session.camera_id}', skipping")
                    continue

                session.register_frame(message["bytes"])
                process_frame(session.camera_id, frame, session)

    except WebSocketDisconnect:
        if session:
            manager.remove(session.camera_id)
    except Exception as e:
        log.error(f"Unexpected error in stream: {e}")
        if session:
            manager.remove(session.camera_id)