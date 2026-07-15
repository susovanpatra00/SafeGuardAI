"""
detect.py
---------
Run the trained smoke/fire model on an image, a folder of images, a
video file, or a live camera stream.

This is a thin wrapper around Ultralytics' predict API, which natively
handles all of those source types. Defaults come from
configs/inference_config.yaml so day-to-day use is just:

    python src/inference/detect.py --source path/to/image.jpg

Source can be:
    - a single image:      test.jpg
    - a folder of images:  data/merged/test/images
    - a video file:        clip.mp4
    - a webcam index:      0
    - a stream URL:        rtsp://...  or  https://...

Examples:
    # single image, default weights from the config
    python src/inference/detect.py --source sample.jpg

    # a whole folder, higher confidence, save YOLO labels too
    python src/inference/detect.py --source data/merged/test/images \
        --conf 0.4 --save-txt

    # a video with a specific checkpoint
    python src/inference/detect.py --source fire_clip.mp4 \
        --weights runs/detect/models/trained/20260715_0724_smoke-fire/weights/best.pt

    # live webcam, show a window
    python src/inference/detect.py --source 0 --show
"""

import argparse
from pathlib import Path

import yaml
from ultralytics import YOLO


def load_config(config_path: Path) -> dict:
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def coerce_source(source: str):
    """A bare integer string ("0") means a webcam index, not a file path."""
    return int(source) if source.isdigit() else source


def run(config_path: Path, overrides: dict):
    cfg = load_config(config_path)
    cfg.update({k: v for k, v in overrides.items() if v is not None})

    weights = Path(cfg["weights"])
    if not weights.exists():
        raise FileNotFoundError(
            f"Weights not found at {weights}.\n"
            f"Set --weights or update `weights:` in {config_path}."
        )

    source = coerce_source(str(cfg["source"]))

    print(f"Weights: {weights}")
    print(f"Source:  {source}")
    print(f"conf={cfg.get('conf', 0.25)}  iou={cfg.get('iou', 0.45)}  "
          f"imgsz={cfg.get('imgsz', 640)}  device={cfg.get('device')}")

    model = YOLO(str(weights))

    results = model.predict(
        source=source,
        conf=cfg.get("conf", 0.25),
        iou=cfg.get("iou", 0.45),
        imgsz=cfg.get("imgsz", 640),
        device=cfg.get("device", None),
        save=cfg.get("save", True),
        save_txt=cfg.get("save_txt", False),
        save_conf=cfg.get("save_conf", False),
        show=cfg.get("show", False),
        project=cfg.get("project_dir", "runs/predict"),
        name=cfg.get("run_name", "predict"),
        exist_ok=False,
        stream=False,
        verbose=True,
    )

    # Brief per-source summary of what was detected.
    names = model.names
    total = {}
    for r in results:
        for c in r.boxes.cls.tolist():
            label = names[int(c)]
            total[label] = total.get(label, 0) + 1

    save_dir = getattr(results[0], "save_dir", cfg.get("project_dir"))
    print("-" * 60)
    print(f"Processed {len(results)} frame(s).")
    print(f"Detections: " + (", ".join(f"{k}={v}" for k, v in total.items()) or "none"))
    if cfg.get("save", True):
        print(f"Annotated output -> {save_dir}")
    return results


def parse_args():
    parser = argparse.ArgumentParser(description="Run smoke/fire detection on any source.")
    parser.add_argument("--config", type=Path, default=Path("configs/inference_config.yaml"))
    parser.add_argument("--source", required=True,
                        help="Image, folder, video, webcam index, or stream URL.")
    parser.add_argument("--weights", type=str, default=None, help="Path to model .pt")
    parser.add_argument("--conf", type=float, default=None)
    parser.add_argument("--iou", type=float, default=None)
    parser.add_argument("--imgsz", type=int, default=None)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--save-txt", dest="save_txt", action="store_true", default=None,
                        help="Also save YOLO-format .txt labels.")
    parser.add_argument("--show", action="store_true", default=None,
                        help="Display a live window (needs a display).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    overrides = {
        "source": args.source,
        "weights": args.weights,
        "conf": args.conf,
        "iou": args.iou,
        "imgsz": args.imgsz,
        "device": args.device,
        "save_txt": args.save_txt,
        "show": args.show,
    }
    run(config_path=args.config, overrides=overrides)
