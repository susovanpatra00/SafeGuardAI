"""
End-to-end live pipeline: RTSP frame -> vehicle detection -> distance
gate -> crop/upscale -> plate detection -> tracking -> periodic OCR ->
validated log entry.

Mirrors scripts/test_video.py but reads from a live RTSP stream instead
of a local file. Swap PlateLogger for your existing SafeGuardAI
alert/notification system when wiring this into the suite.
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
from src.detector.vehicle_detector import VehicleDetector
from src.ocr.plate_ocr import PlateOCR, vote_plate_text
from src.pipeline.cascade import DetectionCascade
from src.pipeline.tracker import PlateTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: str = "configs/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_cascade(cfg: dict) -> DetectionCascade:
    vehicle_detector = VehicleDetector(
        weights_path=cfg["vehicle_detector"]["weights"],
        conf_threshold=cfg["vehicle_detector"]["conf_threshold"],
        iou_threshold=cfg["vehicle_detector"]["iou_threshold"],
        device=cfg["vehicle_detector"]["device"],
        classes=cfg["vehicle_detector"]["classes"],
    )
    plate_detector = PlateDetector(
        weights_path=cfg["detector"]["weights"],
        conf_threshold=cfg["detector"]["conf_threshold"],
        iou_threshold=cfg["detector"]["iou_threshold"],
        device=cfg["detector"]["device"],
    )
    return DetectionCascade(
        vehicle_detector=vehicle_detector,
        plate_detector=plate_detector,
        min_vehicle_height_frac=cfg["distance_gate"]["min_vehicle_height_frac"],
        crop_upscale_size=cfg["detector"]["crop_upscale_size"],
    )


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

    cascade = build_cascade(cfg)
    ocr = PlateOCR(
        model_name=cfg["ocr"]["model_name"],
        device=cfg["ocr"]["device"],
        min_confidence=cfg["ocr"]["min_confidence"],
        validation_regex=cfg["validation"]["regex"] if cfg["validation"]["enabled"] else None,
        strip_chars=cfg["validation"]["strip_chars"],
        format_positions=cfg["validation"].get("format_positions"),
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

            cascade_results = cascade.run(frame)
            vehicle_boxes = [r.vehicle_box for r in cascade_results]
            tracks = tracker.update(vehicle_boxes)
            result_by_box = {r.vehicle_box: r for r in cascade_results}

            for track in tracks:
                if track.frames_since_seen > 0:
                    continue

                result = result_by_box.get(track.box)
                if result is None or result.plate_crop is None:
                    continue  # vehicle close enough, but no plate found this frame

                due_for_ocr = track.frames_since_ocr >= ocr_interval or track.best_text is None
                if not due_for_ocr:
                    continue
                track.frames_since_ocr = 0

                ocr_result = ocr.read(result.plate_crop)
                if ocr_result is None:
                    continue

                track.ocr_history.append((ocr_result.text, ocr_result.confidence))
                voted_text = vote_plate_text(track.ocr_history, cfg["validation"].get("format_positions"))
                track.best_text = voted_text
                is_valid = ocr.validate(voted_text)

                # require a few reads before trusting the vote enough to log —
                # a single read is just that one frame's guess, not yet a consensus
                enough_reads = len(track.ocr_history) >= cfg["ocr"].get("min_reads_before_log", 2)

                if is_valid and enough_reads and not track.logged:
                    max_conf = max(c for _, c in track.ocr_history)
                    plate_logger.log(track.track_id, voted_text, max_conf, is_valid)
                    track.logged = True
                    if cfg["output"]["save_crops"]:
                        crop_path = os.path.join(
                            cfg["output"]["crop_dir"], f"{track.track_id}_{voted_text}.jpg"
                        )
                        cv2.imwrite(crop_path, result.plate_crop)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        stream.stop()


if __name__ == "__main__":
    main()
