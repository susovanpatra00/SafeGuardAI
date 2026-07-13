"""
build_dataset.py  (v2 — final merge stage)
-------------------------------------------
Reads every ingested source under data/normalized/<source_name>/, whose
label files use CANONICAL CLASS NAMES (not ids) — see ingest_external.py
for how that intermediate format gets created.

This script:
  1. Reads data/active_classes.yaml to find which classes are active
  2. Assigns each active class a fresh, contiguous YOLO class id
     (order = the order classes appear in active_classes.yaml)
  3. Walks every source under data/normalized/, filtering each label
     file down to only active-class lines, remapping name -> id
  4. Copies the image + filtered label into data/merged/<split>/
  5. Writes data/merged/data.yaml, ready for Ultralytics training

Because this reads from the ALREADY-INGESTED normalized data (not the
raw downloads), toggling active_classes.yaml and re-running this script
is all you need to do when adding/removing a class — no re-ingestion,
no re-downloading, no manual sorting.

Usage:
    python src/dataset/build_dataset.py
    python src/dataset/build_dataset.py --skip-empty        # drop images with 0 active boxes
    python src/dataset/build_dataset.py --config data/active_classes.yaml
"""

import argparse
import shutil
from pathlib import Path

import yaml

SPLITS = ("train", "valid", "test")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_config(config_path: Path) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_active_classes(cfg: dict) -> list[str]:
    """
    Returns active class names in a STABLE order (insertion order from yaml).
    This order becomes the class-id order in data.yaml — once you start
    training on a given class set, avoid reordering unless retraining
    from scratch is intended.
    """
    classes = cfg["classes"]
    active = [name for name, meta in classes.items() if meta.get("active")]
    if "person" not in active:
        raise ValueError(
            "'person' must be active in active_classes.yaml — it is required "
            "as the anchor box for compliance matching."
        )
    return active


def discover_sources(normalized_dir: Path) -> list[Path]:
    if not normalized_dir.exists():
        return []
    return sorted(p for p in normalized_dir.iterdir() if p.is_dir())


def filter_and_remap_label(label_path: Path, class_to_id: dict) -> list[str]:
    """
    Reads a name-labeled normalized label file, keeps only lines whose
    class name is currently active, remaps name -> numeric id.
    """
    kept = []
    if not label_path.exists():
        return kept

    with open(label_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            # First token is the class NAME here (not an id), rest is bbox.
            # Class names may contain no spaces at this stage since
            # ingest_external.py already normalized them to single tokens
            # (e.g. "Safety Boot" -> "boots"). If yours don't, adjust here.
            cls_name = parts[0]
            coords = parts[1:]

            if cls_name not in class_to_id:
                continue  # inactive right now, drop

            kept.append(f"{class_to_id[cls_name]} {' '.join(coords)}")

    return kept


def build(
    config_path: Path,
    normalized_dir: Path,
    out_dir: Path,
    skip_empty: bool = False,
):
    cfg = load_config(config_path)
    active_classes = get_active_classes(cfg)
    class_to_id = {name: i for i, name in enumerate(active_classes)}

    print(f"Active classes ({len(active_classes)}): {active_classes}")

    sources = discover_sources(normalized_dir)
    if not sources:
        raise FileNotFoundError(
            f"No ingested sources found under {normalized_dir}. "
            f"Run ingest_external.py (or your custom ingestion script) first."
        )
    print(f"Found {len(sources)} ingested source(s): {[s.name for s in sources]}")

    if out_dir.exists():
        print(f"Removing existing merged dataset at {out_dir}")
        shutil.rmtree(out_dir)

    for split in SPLITS:
        (out_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (out_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    totals = {"images": 0, "skipped_empty": 0, "boxes": 0}

    for source_dir in sources:
        for split in SPLITS:
            img_dir = source_dir / split / "images"
            lbl_dir = source_dir / split / "labels"
            if not img_dir.exists():
                continue

            for img_path in sorted(img_dir.iterdir()):
                if img_path.suffix.lower() not in IMAGE_EXTS:
                    continue

                label_path = lbl_dir / f"{img_path.stem}.txt"
                kept_lines = filter_and_remap_label(label_path, class_to_id)

                if skip_empty and len(kept_lines) == 0:
                    totals["skipped_empty"] += 1
                    continue

                dst_img = out_dir / split / "images" / img_path.name
                dst_label = out_dir / split / "labels" / f"{img_path.stem}.txt"

                shutil.copy2(img_path, dst_img)
                with open(dst_label, "w") as f:
                    f.write("\n".join(kept_lines))

                totals["images"] += 1
                totals["boxes"] += len(kept_lines)

    print(f"Total images in merged dataset: {totals['images']}")
    print(f"Total boxes kept: {totals['boxes']}")
    if skip_empty:
        print(f"Images skipped (0 active-class boxes): {totals['skipped_empty']}")

    data_yaml = {
        "path": str(out_dir.resolve()),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(active_classes),
        "names": active_classes,
    }
    data_yaml_path = out_dir / "data.yaml"
    with open(data_yaml_path, "w") as f:
        yaml.dump(data_yaml, f, sort_keys=False)

    print(f"Wrote {data_yaml_path}")
    return data_yaml_path


def parse_args():
    parser = argparse.ArgumentParser(description="Merge normalized sources into a final YOLO dataset.")
    parser.add_argument("--config", type=Path, default=Path("data/active_classes.yaml"))
    parser.add_argument("--normalized-dir", type=Path, default=Path("data/normalized"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/merged"))
    parser.add_argument("--skip-empty", action="store_true",
                         help="Drop images that have zero boxes after filtering to active classes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build(
        config_path=args.config,
        normalized_dir=args.normalized_dir,
        out_dir=args.out_dir,
        skip_empty=args.skip_empty,
    )