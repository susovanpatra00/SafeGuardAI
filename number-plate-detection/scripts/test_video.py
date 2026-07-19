"""
Run the full cascade pipeline (vehicle detection -> distance gate ->
crop/upscale -> plate detection -> tracking -> OCR) against a local
video file. Useful for testing before you have camera access.

Usage:
    python -m scripts.test_video --video inference/your_video.mp4
    python -m scripts.test_video --video inference/your_video.mp4 --save-video
"""

import argparse
import logging
import os

import cv2
import yaml

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


def main(video_path: str, config_path: str = "configs/config.yaml", save_video: bool = False):
    cfg = load_config(config_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.info("Video opened: %s (%dx%d @ %.1f fps)", video_path, width, height, fps)

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

    out_dir = "outputs/video_test"
    os.makedirs(out_dir, exist_ok=True)
    crop_dir = os.path.join(out_dir, "plate_crops")
    os.makedirs(crop_dir, exist_ok=True)
    writer = None
    if save_video:
        out_path = os.path.join(out_dir, "annotated_" + os.path.basename(video_path))
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        logger.info("Will save annotated video to %s", out_path)

    seen_plates = {}
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1

        cascade_results = cascade.run(frame)
        # track on vehicle boxes — vehicles are stable/large, better tracking targets than plates
        vehicle_boxes = [r.vehicle_box for r in cascade_results]
        tracks = tracker.update(vehicle_boxes)

        # match each track back to its cascade result this frame (by box, since tracker just
        # returns updated track boxes — same index order isn't guaranteed so match by box)
        result_by_box = {r.vehicle_box: r for r in cascade_results}

        for track in tracks:
            if track.frames_since_seen > 0:
                continue

            result = result_by_box.get(track.box)
            vx1, vy1, vx2, vy2 = track.box
            cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (255, 128, 0), 2)  # vehicle box, orange

            if result is None or result.plate_crop is None:
                continue  # vehicle close enough, but no plate found in the crop this frame

            px1, py1, px2, py2 = result.plate_box_in_frame
            cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 255, 0), 2)  # plate box, green

            due_for_ocr = track.frames_since_ocr >= cfg["ocr"]["ocr_interval_frames"] or track.best_text is None
            if due_for_ocr:
                track.frames_since_ocr = 0
                crop_path = os.path.join(crop_dir, f"track{track.track_id}_frame{frame_idx}.jpg")
                cv2.imwrite(crop_path, result.plate_crop)

                ocr_result = ocr.read(result.plate_crop)
                if ocr_result is not None:
                    track.ocr_history.append((ocr_result.text, ocr_result.confidence))
                    voted_text = vote_plate_text(track.ocr_history, cfg["validation"].get("format_positions"))
                    is_valid = ocr.validate(voted_text)

                    if voted_text != track.best_text:
                        track.best_text = voted_text
                        seen_plates[track.track_id] = (
                            voted_text,
                            max(c for _, c in track.ocr_history),
                            is_valid,
                        )
                        logger.info(
                            "Frame %d | track %d | voted plate: %s (from %d reads, valid=%s)",
                            frame_idx, track.track_id, voted_text, len(track.ocr_history), is_valid,
                        )

            label = track.best_text or "reading..."
            cv2.putText(frame, label, (px1, max(0, py1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if writer:
            writer.write(frame)

    cap.release()
    if writer:
        writer.release()

    logger.info("Done. %d frames processed.", frame_idx)
    logger.info("Plates read across the video:")
    for track_id, (text, conf, valid) in seen_plates.items():
        logger.info("  track %d: %s (conf=%.2f, valid_format=%s)", track_id, text, conf, valid)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Path to local video file")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--save-video", action="store_true", help="Save annotated output video")
    args = parser.parse_args()
    main(args.video, args.config, args.save_video)
