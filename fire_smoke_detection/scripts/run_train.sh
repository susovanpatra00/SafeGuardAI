#!/usr/bin/env bash
# Build the merged dataset (ingest all sources + merge), then train.
# Run from the fire_smoke_detection/ project root.
set -euo pipefail

bash scripts/run_build.sh

python src/training/train.py \
  --config configs/train_config.yaml \
  --data-yaml data/merged/data.yaml
