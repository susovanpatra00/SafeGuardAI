"""
detector.py - YOLO-based person detector + virtual perimeter breach logic.

Wraps a pretrained YOLO model (person detection only -- no training needed,
see earlier discussion) and checks whether any detected person's center
point falls inside a configured perimeter zone for a given camera.

Handles, per camera:
    - the zone polygon itself
    - debounce (require N consecutive frames before alerting, to avoid
      flicker-triggered false alarms)
    - cooldown (don't re-alert again within N seconds of the last alert)

This module has no knowledge of websockets or FastAPI -- it's a pure
detection/logic layer. server/main.py's process_frame() hook is where
this gets wired into the live stream.
"""

import time
import logging
from dataclasses import dataclass, field

import numpy as np
import cv2
from ultralytics import YOLO

log = logging.getLogger("detector")

PERSON_CLASS_ID = 0  # COCO class 0 = 'person'


@dataclass
class CameraZoneState:
    """Per-camera perimeter + breach-tracking state."""
    polygon: list = field(default_factory=list)   # [(x, y), ...] in frame pixel coords
    inside_streak: int = 0
    last_alert_time: float = 0.0


class PerimeterDetector:
    def __init__(self, model_path="yolov8n.pt", confidence=0.4,
                 frames_to_confirm=3, alert_cooldown_sec=5.0):
        """
        model_path: pretrained YOLO weights. "yolov8n.pt" auto-downloads on
                    first use (~6MB). Swap for yolov8s/m/l/x.pt for more
                    accuracy at the cost of speed -- see earlier discussion.
        confidence: minimum detection confidence (0-1) to count as a person.
        frames_to_confirm: consecutive breached frames required before alerting.
        alert_cooldown_sec: minimum seconds between repeat alerts per camera.
        """
        log.info(f"Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.frames_to_confirm = frames_to_confirm
        self.alert_cooldown_sec = alert_cooldown_sec
        self.camera_zones: dict[str, CameraZoneState] = {}
        log.info("YOLO model loaded.")

    # ---------- Zone management ----------

    def set_zone(self, camera_id: str, polygon: list):
        """Define/update the perimeter polygon for a camera. polygon = [(x,y), ...]"""
        state = self._get_or_create_state(camera_id)
        state.polygon = polygon
        state.inside_streak = 0
        log.info(f"Zone set for '{camera_id}': {len(polygon)} points")

    def get_zone(self, camera_id: str) -> list:
        state = self.camera_zones.get(camera_id)
        return state.polygon if state else []

    def _get_or_create_state(self, camera_id: str) -> CameraZoneState:
        if camera_id not in self.camera_zones:
            self.camera_zones[camera_id] = CameraZoneState()
        return self.camera_zones[camera_id]

    # ---------- Detection ----------

    def detect_people(self, frame: np.ndarray) -> list:
        """
        Run YOLO on a frame, restricted to the 'person' class.
        Returns a list of dicts:
            {"bbox": (x1,y1,x2,y2), "center": (cx,cy), "confidence": float}
        """
        results = self.model(frame, classes=[PERSON_CLASS_ID],
                              conf=self.confidence, verbose=False)
        people = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                people.append({
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "center": (cx, cy),
                    "confidence": conf,
                })
        return people

    # ---------- Breach logic ----------

    def check_breach(self, camera_id: str, people: list) -> dict:
        """
        Given detected people for one frame, check if any fall inside the
        zone, apply debounce + cooldown, and return:
            {"breached": bool, "should_alert": bool, "people_in_zone": [...]}

        "breached" is true any frame someone is in the zone.
        "should_alert" is only true once per cooldown window, after the
        debounce threshold is met -- this is what should actually trigger
        a notification/snapshot, not "breached" directly.
        """
        state = self._get_or_create_state(camera_id)

        if not state.polygon or len(state.polygon) < 3:
            return {"breached": False, "should_alert": False, "people_in_zone": []}

        polygon_np = np.array(state.polygon, dtype=np.int32)
        people_in_zone = [
            person for person in people
            if cv2.pointPolygonTest(polygon_np, person["center"], False) >= 0
        ]

        breached = len(people_in_zone) > 0
        state.inside_streak = state.inside_streak + 1 if breached else 0

        confirmed = state.inside_streak >= self.frames_to_confirm
        cooldown_elapsed = (time.time() - state.last_alert_time) > self.alert_cooldown_sec

        should_alert = confirmed and cooldown_elapsed
        if should_alert:
            state.last_alert_time = time.time()

        return {"breached": breached, "should_alert": should_alert, "people_in_zone": people_in_zone}

    def process_frame(self, camera_id: str, frame: np.ndarray) -> dict:
        """Full pipeline for one frame: detect people, then check zone breach."""
        people = self.detect_people(frame)
        breach = self.check_breach(camera_id, people)
        return {"people": people, "breach": breach}

    # ---------- Visualization (for saved snapshots / debug preview) ----------

    def draw_overlay(self, frame: np.ndarray, camera_id: str, result: dict) -> np.ndarray:
        """Draw the zone, detection boxes, and alert banner onto a copy of the frame."""
        frame = frame.copy()
        state = self.camera_zones.get(camera_id)

        if state and len(state.polygon) >= 3:
            pts = np.array(state.polygon, dtype=np.int32)
            color = (0, 0, 255) if result["breach"]["breached"] else (0, 255, 0)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], color)
            frame = cv2.addWeighted(overlay, 0.2, frame, 0.8, 0)
            cv2.polylines(frame, [pts], True, color, 2)

        in_zone_centers = {p["center"] for p in result["breach"]["people_in_zone"]}
        for person in result["people"]:
            in_zone = person["center"] in in_zone_centers
            color = (0, 0, 255) if in_zone else (0, 255, 0)
            x1, y1, x2, y2 = person["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.circle(frame, person["center"], 4, color, -1)

        if result["breach"]["should_alert"]:
            cv2.putText(frame, "!!! INTRUSION DETECTED !!!", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        return frame