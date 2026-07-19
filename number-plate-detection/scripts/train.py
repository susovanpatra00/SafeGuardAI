from pathlib import Path

from ultralytics import YOLO

DATA_YAML = "data/normalized/indian-number-plate-roboflow/data.yaml"
BASE_WEIGHTS = "yolov8n.pt"  # nano — plate detection is a simple single-class task
EPOCHS = 100
IMG_SIZE = 640
PROJECT_DIR = "outputs/train_runs"
RUN_NAME = "plate_detector_v1"


def main():
    if not Path(DATA_YAML).exists():
        raise SystemExit(
            f"{DATA_YAML} not found. Run ingest_external.py first to normalize the dataset."
        )

    model = YOLO(BASE_WEIGHTS)
    model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        project=PROJECT_DIR,
        name=RUN_NAME,
        patience=20,       # early stop if val loss plateaus
        batch=64,           # fixed batch size — autobatch (-1) triggers a SIGFPE on some
                             # torch/CUDA driver combos during its GPU-memory profiling step.
                             # 64 is conservative for yolov8n @ 640px on an 80GB A100; bump if
                             # GPU utilization looks low, or drop it if you hit OOM.
        device=0,
    )

    best_weights = Path(PROJECT_DIR) / RUN_NAME / "weights" / "best.pt"
    print(f"\nTraining done. Best weights: {best_weights}")
    print("Copy this to models/plate_detector.pt to use it in the live pipeline.")


if __name__ == "__main__":
    main()
