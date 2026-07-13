"""
train.py
--------
Thin wrapper around Ultralytics YOLO training. Reads hyperparameters from
configs/train_config.yaml so you never need to touch this file just to
change epochs, image size, model variant, etc.

Saves each run under models/trained/<run_name>/ so you can compare
different active-class configurations over time instead of overwriting
best.pt every time you retrain (e.g. after adding/removing a class).

Usage:
    python src/training/train.py
    python src/training/train.py --config configs/train_config.yaml
    python src/training/train.py --run-name v2_helmet_vest_boots_gloves
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import yaml
from ultralytics import YOLO


def load_config(config_path: Path) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def default_run_name(data_yaml_path: Path) -> str:
    """
    Builds a descriptive default run name from the active classes in
    data/merged/data.yaml, plus a timestamp, e.g.:
        20260713_1432_person-helmet-vest-boots
    """
    with open(data_yaml_path, "r") as f:
        data_cfg = yaml.safe_load(f)
    class_tag = "-".join(data_cfg["names"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{timestamp}_{class_tag}"


def train(config_path: Path, data_yaml: Path, run_name: str | None):
    cfg = load_config(config_path)

    if run_name is None:
        run_name = default_run_name(data_yaml)

    model_variant = cfg.get("model_variant", "yolov8n.pt")
    epochs = cfg.get("epochs", 100)
    imgsz = cfg.get("imgsz", 640)
    batch = cfg.get("batch", 16)
    device = cfg.get("device", None)  # None lets Ultralytics auto-pick
    patience = cfg.get("patience", 20)
    project_dir = cfg.get("project_dir", "models/trained")

    print(f"Run name:      {run_name}")
    print(f"Model variant: {model_variant}")
    print(f"Data config:   {data_yaml}")
    print(f"Epochs:        {epochs}  |  imgsz: {imgsz}  |  batch: {batch}")

    model = YOLO(model_variant)

    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=patience,
        device=device,
        project=project_dir,
        name=run_name,
        exist_ok=False,
    )

    run_dir = Path(project_dir) / run_name
    best_weights = run_dir / "weights" / "best.pt"

    # Also copy the exact data.yaml used, into the run folder, so you can
    # always trace back exactly which classes/data this run was trained on
    # even after active_classes.yaml changes later.
    if data_yaml.exists():
        shutil.copy2(data_yaml, run_dir / "data_used.yaml")

    print(f"\nTraining complete.")
    print(f"Best weights: {best_weights}")
    print(f"Run directory: {run_dir}")

    return best_weights


def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLO on the merged PPE dataset.")
    parser.add_argument("--config", type=Path, default=Path("configs/train_config.yaml"))
    parser.add_argument("--data-yaml", type=Path, default=Path("data/merged/data.yaml"))
    parser.add_argument("--run-name", type=str, default=None,
                         help="Override the auto-generated run name")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(config_path=args.config, data_yaml=args.data_yaml, run_name=args.run_name)