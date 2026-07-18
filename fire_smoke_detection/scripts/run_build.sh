#!/usr/bin/env bash
# Ingest every source you have (Roboflow and/or manual), then merge them
# into data/merged/. Comment out sources you don't have.
# Run from the fire_smoke_detection/ project root.
set -euo pipefail

# --- Source 1: manual / D-Fire (Kaggle) ---
if [ -d "data/raw/data" ]; then
  python src/dataset/ingest_external.py \
    --source-dir "data/raw/data" \
    --mapping configs/mappings/manual_dfire.yaml \
    --out-dir data/normalized/manual-dfire
fi

# --- Source 2: a Roboflow export ---
if [ -d "data/external/roboflow-firesmoke" ]; then
  python src/dataset/ingest_external.py \
    --source-dir "data/external/roboflow-firesmoke" \
    --mapping configs/mappings/roboflow_firesmoke.yaml \
    --out-dir data/normalized/roboflow-firesmoke
fi

# --- Merge everything under data/normalized/ into data/merged/ ---
python src/dataset/build_dataset.py --skip-empty
