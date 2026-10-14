# number-plate-detection

SafeGuardAI module — automatic number plate recognition (ANPR) on a live RTSP feed.

**Pipeline:** RTSP frame → YOLO plate detection → lightweight IOU tracking (avoid re-OCRing the same plate every frame) → PaddleOCR → regex format validation → CSV log + cropped plate image.

## Setup

```bash
uv sync
```

You'll also need PaddleOCR's model weights, which download automatically on first run (needs internet access once).

## Dataset: Indian Number Plate (Roboflow)

Using [yolox-qcftu/indian-number-plate-keeo5](https://universe.roboflow.com/yolox-qcftu/indian-number-plate-keeo5) — 548 images, single class `number_plate`, CC BY 4.0.

### 1. Download

```bash
export ROBOFLOW_API_KEY="your_key_here"   # from app.roboflow.com -> Settings -> API Keys
python -m scripts.download_dataset
```

This drops the raw YOLOv8-format export into `data/external/indian-number-plate-keeo5/`.

> Check the [dataset page](https://universe.roboflow.com/yolox-qcftu/indian-number-plate-keeo5/dataset/1) for the current version number — the script defaults to version 1, bump `scripts/download_dataset.py` if a newer version exists.

### 2. Normalize / ingest

```bash
python -m src.dataset.ingest_external \
  --source-dir "data/external/indian-number-plate-keeo5" \
  --mapping configs/mappings/indian_number_plate_roboflow.yaml \
  --out-dir data/normalized/indian-number-plate-roboflow
```

This remaps the source's `number_plate` class to a unified `plate` class name (so later, if you merge in a second plate dataset with different class naming, they line up), copies images across, and writes a unified `data.yaml`.

### 3. Train

```bash
python -m scripts.train
```

Defaults: `yolov8n.pt` base, 100 epochs, auto batch size (you're on the A100 80GB, so this'll size up automatically). Single-class detection like this converges fast — expect usable results well before 100 epochs, `patience=20` will early-stop if it plateaus.

Best weights land at `outputs/train_runs/plate_detector_v1/weights/best.pt` — copy that to `models/plate_detector.pt` to plug it into the live pipeline.

```bash
cp outputs/train_runs/plate_detector_v1/weights/best.pt models/plate_detector.pt
```

### 4. Other setup

- **RTSP URL** — set `camera.rtsp_url` in `configs/config.yaml`.
- **Plate format regex** — `validation.regex` defaults to Indian plate format (`XX##XX####`). Adjust or set `validation.enabled: false` to skip filtering.
- 548 images is enough to get a working detector but keep an eye on validation mAP — if it's underwhelming on your actual camera angles/lighting, that's the point to either collect + label more real footage or blend in a second Roboflow set (same `ingest_external.py` pattern, just add a new mapping YAML).

## Run

```bash
python main.py --config configs/config.yaml
```

Logged plates land in `outputs/logs/plate_log.csv`, crops in `outputs/plate_crops/`.

## Notes

- `frame_skip` and `ocr_interval_frames` in the config are your main knobs for GPU load — OCR is the expensive step, so it only re-runs periodically per tracked plate rather than every frame.
- The tracker (`src/pipeline/tracker.py`) is a minimal IOU matcher, not DeepSORT — sufficient here since plates don't need appearance re-identification within a single camera's short dwell time.
- `PlateLogger` is a CSV stub. Swap it for your own alert or webhook system if you want notifications.
