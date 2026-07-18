"""
build_dataset.py
----------------
Final merge stage. Reads every ingested source under
data/normalized/<source>/ (whose label files use CANONICAL CLASS
NAMES, not ids — see ingest_external.py) and merges them into a single
training-ready dataset under data/merged/.

This script:
  1. Reads configs/active_classes.yaml to find which classes are active
  2. Assigns each active class a fresh, contiguous YOLO id
     (order = order in active_classes.yaml, so smoke=0, fire=1)
  3. Walks every source under data/normalized/, filtering each label
     file down to only active-class lines and remapping name -> id
  4. Copies image + filtered label into data/merged/<split>/, prefixing
     filenames with the source name so files from different datasets
     never collide
  5. Writes data/merged/data.yaml, ready for training

Because this reads the ALREADY-NORMALIZED data (not raw downloads),
adding another Roboflow export or manual batch is just: ingest it, then
re-run this. Toggling a class on/off is: edit active_classes.yaml, re-run.

Usage:
    python src/dataset/build_dataset.py
    python src/dataset/build_dataset.py --skip-empty   # drop images with 0 active boxes
    python src/dataset/build_dataset.py --config configs/active_classes.yaml
"""

import argparse
import shutil
from pathlib import Path

import yaml

SPLITS = ("train", "val", "test")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_config(config_path: Path) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_active_classes(cfg: dict) -> list[str]:
    """Active class names in stable insertion order -> defines id order."""
    classes = cfg["classes"]
    active = [name for name, meta in classes.items() if meta.get("active")]
    if not active:
        raise ValueError("No active classes in active_classes.yaml.")
    return active


def discover_sources(normalized_dir: Path) -> list[Path]:
    if not normalized_dir.is_dir():
        return []
    return sorted(p for p in normalized_dir.iterdir() if p.is_dir())


def build(config_path: Path, normalized_dir: Path, merged_dir: Path,
          skip_empty: bool):
    cfg = load_config(config_path)
    active = get_active_classes(cfg)
    name_to_id = {name: i for i, name in enumerate(active)}
    print(f"Active classes: " + ", ".join(f"{i}:{n}" for n, i in name_to_id.items()))

    sources = discover_sources(normalized_dir)
    if not sources:
        raise FileNotFoundError(
            f"No normalized sources found under {normalized_dir}. "
            f"Run src/dataset/ingest_external.py on at least one dataset first."
        )
    print(f"Sources: {[s.name for s in sources]}")

    # Fresh output tree.
    for split in SPLITS:
        (merged_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (merged_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    totals = {split: 0 for split in SPLITS}
    dropped_empty = 0

    for source in sources:
        for split in SPLITS:
            img_dir = source / split / "images"
            lbl_dir = source / split / "labels"
            if not img_dir.is_dir():
                continue

            for img in sorted(img_dir.iterdir()):
                if not img.is_file() or img.suffix.lower() not in IMAGE_EXTS:
                    continue

                label = lbl_dir / (img.stem + ".txt")
                out_lines = []
                if label.exists():
                    for line in label.read_text().splitlines():
                        parts = line.split()
                        if len(parts) != 5:
                            continue
                        cname = parts[0]
                        if cname not in name_to_id:  # inactive class -> skip
                            continue
                        out_lines.append(
                            f"{name_to_id[cname]} {parts[1]} {parts[2]} {parts[3]} {parts[4]}"
                        )

                if skip_empty and not out_lines:
                    dropped_empty += 1
                    continue

                # Prefix with source name to avoid cross-dataset collisions.
                stem = f"{source.name}__{img.stem}"
                shutil.copy2(img, merged_dir / split / "images" / (stem + img.suffix))
                (merged_dir / split / "labels" / (stem + ".txt")).write_text(
                    "\n".join(out_lines) + ("\n" if out_lines else "")
                )
                totals[split] += 1

    # Write data.yaml (val is required by Ultralytics).
    data_cfg: dict = {"names": active, "nc": len(active)}
    for split in SPLITS:
        img_dir = merged_dir / split / "images"
        if any(img_dir.iterdir()):
            data_cfg[split] = str(img_dir.resolve())
    data_yaml_path = merged_dir / "data.yaml"
    with open(data_yaml_path, "w") as f:
        yaml.safe_dump(data_cfg, f, sort_keys=False)

    print("-" * 60)
    for split in SPLITS:
        print(f"  {split}: {totals[split]} images")
    if skip_empty:
        print(f"  (dropped {dropped_empty} images with no active boxes)")
    print(f"Merged dataset -> {merged_dir}")
    print(f"data.yaml      -> {data_yaml_path}")
    return data_yaml_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge all normalized sources into a training-ready dataset."
    )
    parser.add_argument("--config", type=Path, default=Path("configs/active_classes.yaml"))
    parser.add_argument("--normalized-dir", type=Path, default=Path("data/normalized"))
    parser.add_argument("--merged-dir", type=Path, default=Path("data/merged"))
    parser.add_argument("--skip-empty", action="store_true",
                        help="Drop images that end up with 0 active-class boxes.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build(
        config_path=args.config,
        normalized_dir=args.normalized_dir,
        merged_dir=args.merged_dir,
        skip_empty=args.skip_empty,
    )
