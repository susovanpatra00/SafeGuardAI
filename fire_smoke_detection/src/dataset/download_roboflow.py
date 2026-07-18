"""
download_roboflow.py
--------------------
Convenience helper to pull a Roboflow Universe dataset in YOLO format
straight into data/external/<name>/, ready for ingest_external.py.

Needs a free Roboflow API key (Roboflow account -> Settings -> API).
Pass it via --api-key or the ROBOFLOW_API_KEY environment variable.

Find workspace/project/version from the dataset's Roboflow URL, e.g.
    https://universe.roboflow.com/<workspace>/<project>/dataset/<version>

Usage:
    pip install roboflow
    export ROBOFLOW_API_KEY=xxxxxxxx
    python src/dataset/download_roboflow.py \
        --workspace sayed-gamall \
        --project fire-smoke-detection-yolov11 \
        --version 1 \
        --out-dir data/external/roboflow-firesmoke

Then ingest it:
    python src/dataset/ingest_external.py \
        --source-dir data/external/roboflow-firesmoke \
        --mapping configs/mappings/roboflow_firesmoke.yaml \
        --out-dir data/normalized/roboflow-firesmoke
"""

import argparse
import os
import shutil
from pathlib import Path


def download(workspace: str, project: str, version: int, out_dir: Path,
             api_key: str, fmt: str = "yolov8"):
    try:
        from roboflow import Roboflow
    except ImportError as e:
        raise SystemExit(
            "The 'roboflow' package is required. Install it with:\n"
            "    pip install roboflow"
        ) from e

    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    ver = proj.version(version)

    print(f"Downloading {workspace}/{project} v{version} as '{fmt}'...")
    dataset = ver.download(fmt)  # downloads into ./<project>-<version>/

    out_dir.mkdir(parents=True, exist_ok=True)
    src = Path(dataset.location)
    for item in src.iterdir():
        dest = out_dir / item.name
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        shutil.move(str(item), str(dest))
    shutil.rmtree(src, ignore_errors=True)

    print(f"Done -> {out_dir}")
    print("Next: run ingest_external.py with configs/mappings/roboflow_firesmoke.yaml")


def parse_args():
    parser = argparse.ArgumentParser(description="Download a Roboflow dataset in YOLO format.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--format", default="yolov8",
                        help="Roboflow export format (yolov8 works for YOLOv8-v12).")
    parser.add_argument("--api-key", default=os.environ.get("ROBOFLOW_API_KEY"),
                        help="Roboflow API key (or set ROBOFLOW_API_KEY).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.api_key:
        raise SystemExit("No API key. Pass --api-key or set ROBOFLOW_API_KEY.")
    download(args.workspace, args.project, args.version, args.out_dir,
             args.api_key, args.format)
