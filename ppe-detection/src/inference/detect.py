"""
detect.py
---------
End-to-end inference: runs the trained YOLO model on an image/video/
webcam source, matches detected PPE items to detected people, checks
each person's compliance status, and optionally draws + saves the
annotated output.

Usage:
    python src/inference/detect.py --source path/to/image.jpg --weights models/trained/<run>/weights/best.pt
    python src/inference/detect.py --source path/to/video.mp4 --weights models/trained/<run>/weights/best.pt --save
    python src/inference/detect.py --source 0 --weights models/trained/<run>/weights/best.pt   # webcam
"""

import argparse
from pathlib import Path

import cv2
import yaml
from ultralytics import YOLO

from src.inference.person_matcher import Box, match_items_to_people
from src.compliance.checker import check_all_people, load_required_classes

COMPLIANT_COLOR = (0, 200, 0)      # green, BGR
NON_COMPLIANT_COLOR = (0, 0, 255)  # red, BGR
ITEM_COLOR = (255, 180, 0)         # light blue, BGR


def load_matching_config(config_path: str = "data/active_classes.yaml") -> dict:
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("matching", {"iou_threshold": 0.10, "center_contains_fallback": True})


def results_to_boxes(result, class_names: dict) -> tuple[list[Box], list[Box]]:
    """
    Splits a single Ultralytics Results object into (person_boxes, item_boxes).
    """
    person_boxes, item_boxes = [], []

    for box in result.boxes:
        cls_id = int(box.cls[0])
        cls_name = class_names[cls_id]
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        b = Box(x1, y1, x2, y2, cls_name, conf)

        if cls_name == "person":
            person_boxes.append(b)
        else:
            item_boxes.append(b)

    return person_boxes, item_boxes


def draw_annotations(frame, person_boxes, compliance_results, item_boxes):
    for person, result in zip(person_boxes, compliance_results):
        color = COMPLIANT_COLOR if result.compliant else NON_COMPLIANT_COLOR
        label = "COMPLIANT" if result.compliant else f"MISSING: {', '.join(result.missing)}"

        cv2.rectangle(frame, (int(person.x1), int(person.y1)), (int(person.x2), int(person.y2)), color, 2)
        cv2.putText(frame, label, (int(person.x1), max(0, int(person.y1) - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    for item in item_boxes:
        cv2.rectangle(frame, (int(item.x1), int(item.y1)), (int(item.x2), int(item.y2)), ITEM_COLOR, 1)
        cv2.putText(frame, item.class_name, (int(item.x1), max(0, int(item.y1) - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, ITEM_COLOR, 1)

    return frame


def process_frame(frame, model, class_names, required_classes, matching_cfg, imgsz=768, conf=0.25, verbose=False):
    results = model(frame, verbose=False, imgsz=imgsz, conf=conf)[0]

    if verbose:
        print(f"  Raw detections ({len(results.boxes)} total):")
        for box in results.boxes:
            cls_id = int(box.cls[0])
            cls_name = class_names[cls_id]
            conf_val = float(box.conf[0])
            print(f"    {cls_name}: conf={conf_val:.3f}")

    person_boxes, item_boxes = results_to_boxes(results, class_names)

    if verbose:
        print(f"  Raw detections: {len(person_boxes)} person(s), {len(item_boxes)} PPE item(s) "
              f"-> {[b.class_name for b in item_boxes]}")

    assignments = match_items_to_people(
        person_boxes,
        item_boxes,
        iou_threshold=matching_cfg.get("iou_threshold", 0.10),
        center_contains_fallback=matching_cfg.get("center_contains_fallback", True),
    )
    compliance_results = check_all_people(person_boxes, assignments, required_classes)

    if verbose:
        for i, r in enumerate(compliance_results):
            status = "COMPLIANT" if r.compliant else f"NON-COMPLIANT (missing: {r.missing})"
            print(f"  Person {i}: {status}")

    annotated = draw_annotations(frame.copy(), person_boxes, compliance_results, item_boxes)
    return annotated, compliance_results


def run(weights: Path, source: str, active_classes_config: str, save: bool, output_dir: Path, imgsz: int = 768, conf: float = 0.25):
    model = YOLO(str(weights))
    class_names = model.names  # {0: 'person', 1: 'helmet', ...}
    print(f"Model class mapping: {class_names}")

    required_classes = load_required_classes(active_classes_config)
    matching_cfg = load_matching_config(active_classes_config)
    print(f"Required for compliance: {required_classes}")

    is_image = Path(source).suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"} if source not in {"0"} else False

    if is_image:
        frame = cv2.imread(source)
        if frame is None:
            raise FileNotFoundError(f"Could not read image: {source}")
        annotated, compliance_results = process_frame(
            frame, model, class_names, required_classes, matching_cfg, imgsz=imgsz, conf=conf, verbose=True
        )
        if save:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path = output_dir / f"annotated_{Path(source).name}"
            cv2.imwrite(str(out_path), annotated)
            print(f"Saved: {out_path}")
        else:
            cv2.imshow("PPE Compliance", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    else:
        # video file or webcam (source="0")
        cap_source = int(source) if source.isdigit() else source
        cap = cv2.VideoCapture(cap_source)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video source: {source}")

        writer = None
        if save:
            output_dir.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = cap.get(cv2.CAP_PROP_FPS) or 25
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out_path = output_dir / f"annotated_{Path(source).stem if not source.isdigit() else 'webcam'}.mp4"
            writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
            print(f"Saving to: {out_path}")

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            annotated, compliance_results = process_frame(
                frame, model, class_names, required_classes, matching_cfg, imgsz=imgsz, conf=conf, verbose=False
            )

            if writer:
                writer.write(annotated)
            else:
                cv2.imshow("PPE Compliance", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            frame_idx += 1

        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()
        print(f"Processed {frame_idx} frames.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run PPE compliance detection on an image/video/webcam.")
    parser.add_argument("--weights", type=Path, required=True, help="Path to trained best.pt")
    parser.add_argument("--source", type=str, required=True, help="Image/video path, or '0' for webcam")
    parser.add_argument("--config", type=str, default="data/active_classes.yaml")
    parser.add_argument("--save", action="store_true", help="Save output instead of displaying it")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--imgsz", type=int, default=768, help="Must match training imgsz for best results")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.weights, args.source, args.config, args.save, args.output_dir, args.imgsz, args.conf)