"""
train.py
--------
Thin wrapper around Ultralytics YOLO training for Smoke & Fire
detection. Reads hyperparameters from configs/train_config.yaml so
you never need to touch this file just to change epochs, image size,
model variant, etc.

This is the config-driven equivalent of the source notebook's:
    model = YOLO("yolo12n.pt")
    model.train(data=".../data.yaml", epochs=60, imgsz=640, verbose=True)
    model.val()

Each run is saved under models/trained/<run_name>/ so you can compare
different configurations over time instead of overwriting best.pt on
every retrain. A copy of the exact data.yaml used is dropped into the
run folder for full traceability.

Usage:
    python src/training/train.py
    python src/training/train.py --config configs/train_config.yaml
    python src/training/train.py --data-yaml data/clean/data.yaml
    python src/training/train.py --run-name v1_yolo12n_smoke_fire
    python src/training/train.py --no-val        # skip the final validation pass
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
    Builds a descriptive default run name from the class names in
    data.yaml, plus a timestamp, e.g.:
        20260713_1432_smoke-fire
    Falls back gracefully if data.yaml can't be read yet.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    try:
        with open(data_yaml_path, "r") as f:
            data_cfg = yaml.safe_load(f)
        class_tag = "-".join(data_cfg["names"])
    except Exception:
        class_tag = "smoke-fire"
    return f"{timestamp}_{class_tag}"


def train(config_path: Path, data_yaml: Path, run_name: str | None,
          run_val: bool = True):
    cfg = load_config(config_path)

    if run_name is None:
        run_name = default_run_name(data_yaml)

    model_variant = cfg.get("model_variant", "yolo12n.pt")
    epochs = cfg.get("epochs", 60)
    imgsz = cfg.get("imgsz", 640)
    batch = cfg.get("batch", 16)
    device = cfg.get("device", None)  # None lets Ultralytics auto-pick
    patience = cfg.get("patience", 20)
    verbose = cfg.get("verbose", True)
    project_dir = cfg.get("project_dir", "models/trained")

    if not data_yaml.exists():
        raise FileNotFoundError(
            f"data.yaml not found at {data_yaml}. Build the merged dataset first:\n"
            f"    python src/dataset/ingest_external.py ...   # per source\n"
            f"    python src/dataset/build_dataset.py         # merge -> {data_yaml}"
        )

    print(f"Run name:      {run_name}")
    print(f"Model variant: {model_variant}")
    print(f"Data config:   {data_yaml}")
    print(f"Epochs:        {epochs}  |  imgsz: {imgsz}  |  batch: {batch}")

    model = YOLO(model_variant)

    model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=patience,
        device=device,
        verbose=verbose,
        project=project_dir,
        name=run_name,
        exist_ok=False,
    )

    # Use the ACTUAL directory Ultralytics saved to (don't reconstruct it —
    # Ultralytics may resolve `project` under its own runs/ dir).
    try:
        run_dir = Path(model.trainer.save_dir)
    except Exception:
        run_dir = Path(project_dir) / run_name
    best_weights = run_dir / "weights" / "best.pt"

    # Snapshot the exact data.yaml used, so this run stays traceable
    # even if the dataset/config changes later. Never let this kill the run.
    try:
        if data_yaml.exists() and run_dir.is_dir():
            shutil.copy2(data_yaml, run_dir / "data_used.yaml")
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] could not copy data_used.yaml: {e}")

    if run_val:
        print("\nRunning final validation pass...")
        model.val()

    print("\nTraining complete.")
    print(f"Best weights:  {best_weights}")
    print(f"Run directory: {run_dir}")

    return best_weights


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train YOLO on the cleaned smoke/fire dataset."
    )
    parser.add_argument("--config", type=Path, default=Path("configs/train_config.yaml"))
    parser.add_argument("--data-yaml", type=Path, default=Path("data/merged/data.yaml"))
    parser.add_argument("--run-name", type=str, default=None,
                        help="Override the auto-generated run name")
    parser.add_argument("--no-val", action="store_true",
                        help="Skip the final validation pass after training")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(
        config_path=args.config,
        data_yaml=args.data_yaml,
        run_name=args.run_name,
        run_val=not args.no_val,
    )
