# Fire & Smoke Detection (YOLOv12)

Real-time smoke and fire detection built on Ultralytics YOLO. Ported from
the `smoke-fire-detection-yolo-v12` notebook into a **config-driven,
multi-source** pipeline that mirrors the sibling `ppe-detection` project.

Two canonical classes: `smoke` (id 0), `fire` (id 1).

## Why "multi-source"?

You can train on **Roboflow exports and your own manual data at the same
time**. Each dataset is a "source". You *ingest* each source through a
mapping file that translates its class names into the canonical ones, then
*build* merges every ingested source into a single training set. Different
sources can have different class names/order — the mapping handles it.

```
raw datasets ──ingest──▶ data/normalized/<source>/ ──build──▶ data/merged/ ──train──▶ model
 (roboflow,             (labels use canonical           (fresh class ids,
  manual, ...)           class NAMES)                    one data.yaml)
```

## Layout

```
fire_smoke_detection/
├── configs/
│   ├── active_classes.yaml          # canonical classes + id order (smoke, fire)
│   ├── train_config.yaml            # model variant + hyperparameters
│   └── mappings/
│       ├── roboflow_firesmoke.yaml  # map a Roboflow export -> canonical
│       └── manual_dfire.yaml        # map manual/D-Fire data + bad-image list
├── scripts/
│   ├── run_build.sh                 # ingest all sources + merge
│   └── run_train.sh                 # build + train end-to-end
└── src/
    ├── dataset/
    │   ├── download_roboflow.py     # pull a Roboflow dataset via API (optional)
    │   ├── ingest_external.py       # normalize ONE source -> canonical names
    │   └── build_dataset.py         # merge all normalized sources -> data/merged
    └── training/train.py            # config-driven YOLO training wrapper
```

## Setup

```bash
cd fire_smoke_detection
uv sync            # or: pip install -e .
```

## Getting data

### Option A — Manual / Kaggle (the notebook's dataset)

Download **smoke-fire-detection-yolo** (the D-Fire set) and unzip so you get:

```
data/raw/smoke-fire-detection-yolo/
├── train/{images,labels}
├── val/{images,labels}
└── test/{images,labels}
```

```bash
pip install kaggle
kaggle datasets download -d sayedgamal99/smoke-fire-detection-yolo -p data/raw --unzip
```

The `manual_dfire.yaml` mapping already carries the notebook's bad-image
quarantine list and declares the class order (0=smoke, 1=fire).

Any **hand-labeled** YOLO dataset works the same way — point a mapping at it.

### Option B — Roboflow

Grab a fire/smoke dataset from Roboflow Universe (e.g. `sayed-gamall/
fire-smoke-detection-yolov11`). Either export → "YOLOv8" → download the zip
into `data/external/roboflow-firesmoke/`, or use the helper:

```bash
pip install roboflow
export ROBOFLOW_API_KEY=xxxx
python src/dataset/download_roboflow.py \
  --workspace sayed-gamall --project fire-smoke-detection-yolov11 \
  --version 1 --out-dir data/external/roboflow-firesmoke
```

Roboflow exports ship their own `data.yaml`, so `ingest_external.py` reads
the source class order automatically — you only edit the mapping if the
class names differ from what `roboflow_firesmoke.yaml` already covers.

**You can use A and B together** — ingest both, then build once.

## Pipeline

### 1. Ingest each source (normalize + clean)

```bash
# manual / D-Fire
python src/dataset/ingest_external.py \
  --source-dir data/raw/smoke-fire-detection-yolo \
  --mapping configs/mappings/manual_dfire.yaml \
  --out-dir data/normalized/manual-dfire

# a roboflow export
python src/dataset/ingest_external.py \
  --source-dir data/external/roboflow-firesmoke \
  --mapping configs/mappings/roboflow_firesmoke.yaml \
  --out-dir data/normalized/roboflow-firesmoke
```

Ingest quarantines listed-bad and OpenCV-undecodable images, drops classes
mapped to `null`, and writes labels using canonical class *names*.

### 2. Merge into one training set

```bash
python src/dataset/build_dataset.py --skip-empty
```

Reads `active_classes.yaml`, assigns fresh ids (smoke=0, fire=1), merges
every source under `data/normalized/` into `data/merged/` (filenames are
prefixed with the source name so nothing collides), and writes
`data/merged/data.yaml`.

### 3. Train

```bash
python src/training/train.py
```

Hyperparameters come from `configs/train_config.yaml` (default `yolo12n.pt`,
60 epochs, imgsz 640). Runs land in `models/trained/<run_name>/` with a copy
of the exact `data.yaml` used. A validation pass runs at the end (`--no-val`
to skip).

Or all at once:

```bash
bash scripts/run_train.sh
```

## Adding another dataset later

1. Drop it under `data/external/<name>/` (or `data/raw/<name>/`).
2. Add a mapping in `configs/mappings/` (copy an existing one, fix the class
   names / `source_names`).
3. `ingest_external.py` it into `data/normalized/<name>/`.
4. Re-run `build_dataset.py`. No code changes needed.

## Notes

- To add a class (say `person`), set it `active: true` in
  `active_classes.yaml` and map some source class to it in a mapping file,
  then re-ingest that source and rebuild.
- Change the backbone via `model_variant` in `train_config.yaml`
  (`yolo12s.pt`, `yolo12m.pt`, or older `yolov8n.pt`, etc.).
- Set `device` to `mps` (Apple Silicon), `cpu`, or a GPU index like `0`;
  `null` lets Ultralytics auto-select.
