"""
ingest_external.py
------------------
Normalizes ONE external YOLO-format dataset (a Roboflow export OR your
own manual/D-Fire images) into our intermediate "normalized" format,
using a per-source mapping file to translate that dataset's class names
into OUR canonical names (see configs/active_classes.yaml).

Why an intermediate format instead of writing straight to data/merged?
    Because active_classes.yaml can change over time, and you may have
    several sources (Roboflow + manual) with different class orders.
    Baking in numeric ids at ingest time would mean re-ingesting every
    time you toggle a class. Instead we write labels with the CANONICAL
    CLASS NAME as plain text, and build_dataset.py assigns numeric ids
    fresh, every time, from whatever is active right now.

Cleaning is folded in here (ported from the notebook):
    - images listed in the mapping's `bad_images` are quarantined
    - images OpenCV can't decode are quarantined
    - source classes mapped to null (or not in the mapping) are dropped

Normalized label line format (intermediate only, NOT standard YOLO):
    <canonical_class_name> <cx> <cy> <w> <h>

Usage:
    # Roboflow export (has its own data.yaml):
    python src/dataset/ingest_external.py \
        --source-dir "data/external/roboflow-firesmoke" \
        --mapping configs/mappings/roboflow_firesmoke.yaml \
        --out-dir data/normalized/roboflow-firesmoke

    # Manual / D-Fire (class order comes from the mapping's source_names):
    python src/dataset/ingest_external.py \
        --source-dir "data/raw/smoke-fire-detection-yolo" \
        --mapping configs/mappings/manual_dfire.yaml \
        --out-dir data/normalized/manual-dfire
"""

import argparse
import shutil
from pathlib import Path

import cv2
import yaml

SPLITS = ("train", "val", "valid", "test")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def resolve_source_names(source_dir: Path, mapping_cfg: dict) -> list[str]:
    """
    Figure out the class-name order of the RAW source labels.
    Priority:
      1. `source_names` explicitly listed in the mapping file
      2. the source's own data.yaml `names` (Roboflow exports have this)
    """
    if mapping_cfg.get("source_names"):
        return list(mapping_cfg["source_names"])

    data_yaml = source_dir / "data.yaml"
    if data_yaml.exists():
        names = load_yaml(data_yaml).get("names")
        if isinstance(names, dict):  # some exports use {0:'a',1:'b'}
            names = [names[i] for i in range(len(names))]
        if names:
            return list(names)

    raise ValueError(
        f"Could not determine source class names for {source_dir}. "
        f"Add `source_names: [...]` to the mapping file, or ensure the "
        f"source has a data.yaml with a `names` list."
    )


def is_valid_image(image_path: Path) -> bool:
    """True if OpenCV can decode the file into a non-empty image."""
    try:
        img = cv2.imread(str(image_path))
        return img is not None and img.size != 0
    except Exception as e:  # noqa: BLE001
        print(f"  [error] could not read {image_path}: {e}")
        return False


def ingest_split(source_dir: Path, split: str, id_to_canonical: dict,
                 bad_set: set[str], out_dir: Path) -> dict:
    img_dir = source_dir / split / "images"
    lbl_dir = source_dir / split / "labels"
    if not img_dir.is_dir():
        return {}

    # Normalize the output split name: fold "valid" -> "val".
    out_split = "val" if split == "valid" else split
    out_img_dir = out_dir / out_split / "images"
    out_lbl_dir = out_dir / out_split / "labels"
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    stats = {"kept": 0, "quarantined": 0, "boxes_kept": 0, "boxes_dropped": 0}

    for src_img in sorted(img_dir.iterdir()):
        if not src_img.is_file() or src_img.suffix.lower() not in IMAGE_EXTS:
            continue

        rel = f"{split}/images/{src_img.name}"
        listed_bad = rel in bad_set
        if listed_bad or not is_valid_image(src_img):
            stats["quarantined"] += 1
            continue

        # Remap this image's label lines to canonical class names.
        src_label = lbl_dir / (src_img.stem + ".txt")
        out_lines = []
        if src_label.exists():
            for line in src_label.read_text().splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue
                cls_id = int(float(parts[0]))
                canonical = id_to_canonical.get(cls_id)  # None => drop class
                if canonical is None:
                    stats["boxes_dropped"] += 1
                    continue
                out_lines.append(f"{canonical} {parts[1]} {parts[2]} {parts[3]} {parts[4]}")
                stats["boxes_kept"] += 1

        shutil.copy2(src_img, out_img_dir / src_img.name)
        (out_lbl_dir / (src_img.stem + ".txt")).write_text(
            "\n".join(out_lines) + ("\n" if out_lines else "")
        )
        stats["kept"] += 1

    return stats


def ingest(source_dir: Path, mapping_path: Path, out_dir: Path):
    mapping_cfg = load_yaml(mapping_path)
    name_map: dict = mapping_cfg.get("mapping", {})
    bad_set = {str(Path(p)) for p in mapping_cfg.get("bad_images", [])}

    source_names = resolve_source_names(source_dir, mapping_cfg)

    # Build source-id -> canonical-name (None means "drop this class").
    id_to_canonical: dict[int, str | None] = {}
    unknown = set()
    for idx, sname in enumerate(source_names):
        if sname in name_map:
            id_to_canonical[idx] = name_map[sname]  # may be None
        else:
            id_to_canonical[idx] = None
            unknown.add(sname)

    print(f"Source:   {source_dir}")
    print(f"Mapping:  {mapping_path.name}  ({mapping_cfg.get('source_dataset','?')})")
    print(f"Classes:  " + ", ".join(
        f"{i}:{n}->{id_to_canonical[i]}" for i, n in enumerate(source_names)))
    if unknown:
        print(f"  [warn] source classes not in mapping (dropped): {sorted(unknown)}")

    total = {"kept": 0, "quarantined": 0, "boxes_kept": 0, "boxes_dropped": 0}
    for split in ("train", "val", "valid", "test"):
        s = ingest_split(source_dir, split, id_to_canonical, bad_set, out_dir)
        for k, v in s.items():
            total[k] += v

    print("-" * 60)
    print(f"Kept images:  {total['kept']}   quarantined: {total['quarantined']}")
    print(f"Kept boxes:   {total['boxes_kept']}   dropped boxes: {total['boxes_dropped']}")
    print(f"Normalized -> {out_dir}")
    return total


def parse_args():
    parser = argparse.ArgumentParser(
        description="Normalize one YOLO dataset (Roboflow or manual) to canonical classes."
    )
    parser.add_argument("--source-dir", type=Path, required=True,
                        help="Root of the source dataset (contains train/val/test).")
    parser.add_argument("--mapping", type=Path, required=True,
                        help="Per-source mapping file under configs/mappings/.")
    parser.add_argument("--out-dir", type=Path, required=True,
                        help="Where to write normalized output, e.g. data/normalized/<name>.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingest(source_dir=args.source_dir, mapping_path=args.mapping, out_dir=args.out_dir)
