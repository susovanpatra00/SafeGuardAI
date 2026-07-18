#!/usr/bin/env bash
# Run detection on a source (image / folder / video / webcam index).
# Usage: bash scripts/run_inference.sh <source> [extra args...]
#   bash scripts/run_inference.sh sample.jpg
#   bash scripts/run_inference.sh data/merged/test/images --conf 0.4
#   bash scripts/run_inference.sh clip.mp4
#   bash scripts/run_inference.sh 0 --show
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: bash scripts/run_inference.sh <source> [extra args...]"
  exit 1
fi

SOURCE="$1"; shift
python src/inference/detect.py --source "$SOURCE" "$@"
