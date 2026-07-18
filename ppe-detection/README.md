# PPE Detection — SafeGuardAI

Detects **person, helmet, vest, boots** (plus bonus classes: gloves, goggles) on
construction-site imagery, matches each PPE item to the correct person, and
flags each person as **COMPLIANT** or **NON-COMPLIANT** based on missing
required items.

This module is built to be **modular** — datasets, active classes, and model
choice can all be swapped without touching code. See `data/active_classes.yaml`
to add/remove classes, and the pipeline below to add/remove data sources.

---

## 1. Setup

```bash
git clone <repo-url>
cd SafeGuardAI/ppe-detection
uv sync
```

Fix the Ultralytics output-path bug once per fresh environment:
```bash
yolo settings runs_dir=''
```

---

## 2. Datasets

We combine **three sources** for the best results found so far. Each has a
mapping config in `configs/mappings/` that translates its own class names
into our canonical set (`person, helmet, vest, boots, gloves, goggles`, plus
negative classes `no_helmet, no_goggle, no_gloves, no_boots`, and `none`).

| Source | Images | Notes |
|---|---|---|
| `skcet` (Roboflow) | ~8,845 | Large volume, mixed quality, strong on boots |
| `ketakichalke` / Ultralytics Construction-PPE | ~1,416 | Small, clean, curated, real construction sites |
| `SH17` | ~8,099 | Large, diverse industrial scenes. **CC BY-NC-SA 4.0 — non-commercial only.** Used here for demo purposes; do not ship in the client-facing product without checking licensing. |

**Explicitly excluded** (tested, made results worse or didn't fit our classes):
Roboflow "Construction Site Safety" (contaminated with stock photos/joggers/ads),
SFCHD (wrong domain, no vest/boots class), Hard Hat Detection / SHEL5K (no
vest/boots, known incomplete person labeling).

### 2a. Download `skcet`

1. Go to https://universe.roboflow.com/skcet-g4h72/construction-ppe-rdhzo
2. Download Dataset → format **YOLOv8** → unzip into `data/external/skcet_data/`

Expected layout: `train/`, `valid/`, `test/` each with `images/` + `labels/`, plus `data.yaml`.

### 2b. Download `ketakichalke`

Kaggle dataset: `ketakichalke/ppe-kit-detection-construction-site-workers`
(This is the same data as the official Ultralytics Construction-PPE dataset.)

```bash
pip install kaggle --break-system-packages
mkdir -p ~/.kaggle
# place your kaggle.json API token at ~/.kaggle/kaggle.json (get it from
# kaggle.com -> Account -> Create New API Token). NEVER commit this file.
chmod 600 ~/.kaggle/kaggle.json

kaggle datasets download -d ketakichalke/ppe-kit-detection-construction-site-workers \
  -p data/external/ketakichalke_data --unzip
```

This downloads with a flat `images/{train,val,test}` + `labels/{train,val,test}`
layout. Reorganize to our expected `train/valid/test` split-per-folder layout:

```bash
cd data/external/ketakichalke_data
mkdir -p train/images train/labels valid/images valid/labels test/images test/labels
mv images/train/* train/images/   && mv labels/train/* train/labels/
mv images/val/*   valid/images/   && mv labels/val/*   valid/labels/
mv images/test/*  test/images/    && mv labels/test/*  test/labels/
rm -f labels/train.cache labels/val.cache
rmdir images labels 2>/dev/null

cat > data.yaml << 'EOF'
train: ../train/images
val: ../valid/images
test: ../test/images
nc: 11
names: ['helmet', 'gloves', 'vest', 'boots', 'goggles', 'none', 'Person', 'no_helmet', 'no_goggle', 'no_gloves', 'no_boots']
EOF

cd ../../..
```

### 2c. Download `SH17`

Kaggle dataset: `mugheesahmad/sh17-dataset-for-ppe-detection`

```bash
kaggle datasets download -d mugheesahmad/sh17-dataset-for-ppe-detection \
  -p data/external/sh17_data --unzip
```

This ships flat (`images/`, `labels/`, `train_files.txt`, `val_files.txt`, CRLF
line endings). Reorganize:

```bash
cd data/external/sh17_data
mkdir -p train/images train/labels valid/images valid/labels

while IFS= read -r fname; do
  fname="${fname%$'\r'}"
  mv "images/$fname" "train/images/" 2>/dev/null
done < train_files.txt
while IFS= read -r fname; do
  fname="${fname%$'\r'}"
  mv "images/$fname" "valid/images/" 2>/dev/null
done < val_files.txt

while IFS= read -r fname; do
  fname="${fname%$'\r'}"
  stem="${fname%.*}"
  mv "labels/$stem.txt" "train/labels/" 2>/dev/null
done < train_files.txt
while IFS= read -r fname; do
  fname="${fname%$'\r'}"
  stem="${fname%.*}"
  mv "labels/$stem.txt" "valid/labels/" 2>/dev/null
done < val_files.txt

cat > data.yaml << 'EOF'
train: ../train/images
val: ../valid/images
test:
nc: 17
names:
  0: person
  1: ear
  2: ear-mufs
  3: face
  4: face-guard
  5: face-mask
  6: foot
  7: tool
  8: glasses
  9: gloves
  10: helmet
  11: hands
  12: head
  13: medical-suit
  14: shoes
  15: safety-suit
  16: safety-vest
EOF

cd ../../..
```

---

## 3. Ingest + merge

Each source gets normalized into a common intermediate format (name-based
labels, not yet numeric IDs — that mapping happens fresh at merge time based
on whatever's active in `data/active_classes.yaml`).

```bash
python -m src.dataset.ingest_external \
  --source-dir "data/external/skcet_data" \
  --mapping configs/mappings/construction_ppe_skcet.yaml \
  --out-dir data/normalized/construction-ppe-skcet

python -m src.dataset.ingest_external \
  --source-dir "data/external/ketakichalke_data" \
  --mapping configs/mappings/construction_ppe_ultralytics.yaml \
  --out-dir data/normalized/ketakichalke

python -m src.dataset.ingest_external \
  --source-dir "data/external/sh17_data" \
  --mapping configs/mappings/sh17.yaml \
  --out-dir data/normalized/sh17
```

Merge everything into the final training-ready dataset:

```bash
python -m src.dataset.build_dataset --skip-empty
```

Output: `data/merged/{train,valid,test}/{images,labels}` + `data/merged/data.yaml`.

**To add/remove a class later:** edit `data/active_classes.yaml`
(`active: true/false`), then just re-run `build_dataset` — no re-ingestion
needed, since the normalized data already has all classes available.

**To add a new dataset source later:** write a new mapping config under
`configs/mappings/`, run `ingest_external.py` once, then re-run
`build_dataset.py`.

---

## 4. Training

Hyperparameters live in `configs/train_config.yaml` (model variant, epochs,
image size, batch, device, etc.) — edit that file, not the training script.

```bash
python src/training/train.py
```

Weights land at `models/trained/<run_name>/weights/best.pt`, where
`<run_name>` auto-includes a timestamp and the active class list, so
different training runs never overwrite each other.

**Best result so far:** YOLO11s, all 3 sources combined, 11 classes trained
(so the model also learns gloves/goggles/negative-class context even though
compliance only requires helmet/vest/boots) — `person` mAP50-95: 0.705,
`vest`: 0.730, `helmet`: 0.678, `boots`: 0.587.

---

## 5. Inference

`detect.py` accepts a single image, a single video, a webcam (`--source 0`),
**or a whole folder** containing a mix of images and videos — it auto-detects
and processes everything inside.

```bash
# single image
python -m src.inference.detect \
  --weights models/trained/<run_name>/weights/best.pt \
  --source path/to/image.jpg \
  --imgsz 768 --conf 0.25 --save

# single video
python -m src.inference.detect \
  --weights models/trained/<run_name>/weights/best.pt \
  --source path/to/video.mp4 \
  --imgsz 768 --conf 0.25 --save

# webcam (live, displays a window instead of saving — omit --save)
python -m src.inference.detect \
  --weights models/trained/<run_name>/weights/best.pt \
  --source 0

# whole folder of images and/or videos in one call
python -m src.inference.detect \
  --weights models/trained/<run_name>/weights/best.pt \
  --source path/to/folder/ \
  --imgsz 768 --conf 0.25 --save
```

- `--source` accepts an image path, a video path, a folder path, or `0` for webcam.
- `--save` writes to `--output-dir` (default `outputs/`); omit it to display in a window instead (not available for folder mode — folders always save).
- Output shows each detected person's box in **green (compliant)** or **red (non-compliant, with missing items listed)**, plus individual PPE item boxes in blue. Negative-class detections (`no_helmet`, `no_goggle`, etc.) are intentionally not drawn — they're redundant with the MISSING label and confusing in a demo.
- `--imgsz` should match whatever `imgsz` was used in training (currently 768) — mismatches hurt small-object detection (helmet, boots) noticeably.

Compliance rules (which classes are required) are read live from
`data/active_classes.yaml` at inference time — no retraining needed to change
what counts as "compliant," only to change what the model can *detect*.

### Demo / POC test media

Real (non-dataset) test images and videos for demos live in
`data/test_samples/{images,videos}/` — gitignored, since this may include
client-provided or otherwise non-redistributable footage. Drop files there
and run:

```bash
WEIGHTS="models/trained/<run_name>/weights/best.pt"

python -m src.inference.detect \
  --weights "$WEIGHTS" \
  --source data/test_samples \
  --imgsz 768 --conf 0.25 \
  --save --output-dir outputs/poc_demo
```

Annotated output lands in `outputs/poc_demo/` (also gitignored), ready to
download and present.

Make sure both are excluded from git if not already:
```
data/test_samples/
outputs/
```

---

## 6. Known limitations (honest notes for whoever picks this up next)

- **SH17** contains a meaningful fraction of non-construction stock photos
  (offices, medical settings, etc.) — the model correctly detects "no PPE"
  on these, but they're not representative of real deployment footage.
- **SH17's `glasses` class** maps loosely to `goggles` in our mapping, but
  SH17 labels *any* eyewear (including regular glasses) this way — so our
  `goggles` class is noisier than helmet/vest/boots. Not used for
  compliance, so low-impact, but worth fixing if goggles ever becomes a
  required class.
- **`person` detection is still the weakest of the 3 required-for-compliance
  classes** relative to helmet/vest/boots, though it improved substantially
  (0.45 → 0.705 mAP50-95) once all 3 sources were combined. Tight upper-body
  crops (vs. full-body shots) seem to be a harder case specifically.
- For a real client deployment, prioritize testing on **actual client camera
  footage** over these public datasets — public data got us a working demo,
  but real-world camera angle/distance/lighting will differ.