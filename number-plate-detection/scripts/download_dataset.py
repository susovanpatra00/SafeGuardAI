"""
Downloads the Indian number plate dataset from Roboflow Universe.

Requires a free Roboflow account + API key:
  1. https://app.roboflow.com -> Settings -> API Keys
  2. export ROBOFLOW_API_KEY="your_key_here"   (or pass --api-key)

Usage:
    python -m scripts.download_dataset --api-key $ROBOFLOW_API_KEY
"""

import argparse
import os

from roboflow import Roboflow


def download(api_key: str, out_dir: str = "data/external"):
    rf = Roboflow(api_key=api_key)
    project = rf.workspace("yolox-qcftu").project("indian-number-plate-keeo5")
    version = project.version(1)  # check universe page for latest version number
    dataset = version.download("yolov8", location=os.path.join(out_dir, "indian-number-plate-keeo5"))
    print(f"Downloaded to: {dataset.location}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("ROBOFLOW_API_KEY"))
    parser.add_argument("--out-dir", default="data/external")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit(
            "No API key provided. Pass --api-key or set ROBOFLOW_API_KEY env var."
        )
    download(args.api_key, args.out_dir)
