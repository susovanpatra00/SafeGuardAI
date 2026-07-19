"""
End-to-end pipeline: RTSP frame -> plate detection -> tracking ->
periodic OCR -> validated log entry.

This is the same "glue file" pattern as your other SafeGuardAI modules
(alerts/engine.py style) — swap the AlertSink at the bottom for your
existing alert/notification system when you wire this into the suite.
"""

import csv
import logging
import os
import time
from datetime import datetime, timezone

import cv2
import yaml

from src.cameras.stream import RTSPStream, StreamConfig
from src.detector.plate_detector import PlateDetector
from src.ocr.plate_ocr import PlateOCR
from src.pipeline.tracker import PlateTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: str = "configs/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class PlateLogger:
    """Writes one row per confirmed plate read. Swap for a DB/webhook later."""

    def __init__(self, log_dir: str):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, "plate_log.csv")
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="") as f:
                csv.writer(f).writerow(["timestamp_utc", "track_id", "plate_text", "confidence", "valid_format"])

    def log(self, track_id: int, text: str, confidence: float, valid: bool):
        with open(self.path, "a", newline="") as f:
            csv.writer(f).writerow(
                [datetime.now(timezone.utc).isoformat(), track_id, text, f"{confidence:.3f}", valid]
            )
        logger.info("Plate logged: id=%s text=%s conf=%.2f valid=%s", track_id, text, confidence, valid)


def main(config_path: str = "configs/config.yaml"):
    cfg = load_config(config_path)

    stream = RTSPStream(
        StreamConfig(
            rtsp_url=cfg["camera"]["rtsp_url"],
            reconnect_delay_sec=cfg["camera"]["reconnect_delay_sec"],
            target_width=cfg["camera"]["target_width"],
        )
    )
    stream.start()

    detector = PlateDetector(
        weights_path=cfg["detector"]["weights"],
        conf_threshold=cfg["detector"]["conf_threshold"],
        iou_threshold=cfg["detector"]["iou_threshold"],
        device=cfg["detector"]["device"],
    )

    ocr = PlateOCR(
        lang=cfg["ocr"]["lang"],
        use_angle_cls=cfg["ocr"]["use_angle_cls"],
        min_confidence=cfg["ocr"]["min_confidence"],
        validation_regex=cfg["validation"]["regex"] if cfg["validation"]["enabled"] else None,
        strip_chars=cfg["validation"]["strip_chars"],
    )

    tracker = PlateTracker(
        iou_threshold=cfg["tracking"]["iou_match_threshold"],
        max_missed_frames=cfg["tracking"]["max_missed_frames"],
    )

    plate_logger = PlateLogger(cfg["output"]["log_dir"])
    if cfg["output"]["save_crops"]:
        os.makedirs(cfg["output"]["crop_dir"], exist_ok=True)

    frame_skip = cfg["camera"]["frame_skip"]
    ocr_interval = cfg["ocr"]["ocr_interval_frames"]
    frame_count = 0

    logger.info("Pipeline running. Waiting for frames...")
    try:
        while True:
            frame = stream.read()
            if frame is None:
                time.sleep(0.05)
                continue

            frame_count += 1
            if frame_count % frame_skip != 0:
                continue

            detections = detector.detect(frame)
            tracks = tracker.update([d.box for d in detections])

            for track in tracks:
                if track.frames_since_seen > 0:
                    continue  # not matched this frame

                due_for_ocr = track.frames_since_ocr >= ocr_interval or track.best_text is None
                if not due_for_ocr:
                    continue
                track.frames_since_ocr = 0

                x1, y1, x2, y2 = track.box
                crop = frame[y1:y2, x1:x2]
                result = ocr.read(crop)
                if result is None:
                    continue

                if result.confidence > track.best_confidence:
                    track.best_text = result.text
                    track.best_confidence = result.confidence

                if result.is_valid_format and not track.logged:
                    plate_logger.log(track.track_id, result.text, result.confidence, result.is_valid_format)
                    track.logged = True
                    if cfg["output"]["save_crops"]:
                        crop_path = os.path.join(
                            cfg["output"]["crop_dir"], f"{track.track_id}_{result.text}.jpg"
                        )
                        cv2.imwrite(crop_path, crop)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        stream.stop()


if __name__ == "__main__":
    main()
