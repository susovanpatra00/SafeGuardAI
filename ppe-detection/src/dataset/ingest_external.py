"""
ingest_external.py
-------------------
Normalizes an externally downloaded YOLO-format dataset (e.g. from
Roboflow Universe) into our intermediate "normalized" format, using a
per-source mapping file to translate that dataset's class names into
OUR canonical class names.

Why an intermediate format instead of going straight to data/merged?
    Because active_classes.yaml can change over time (you might enable
    gloves later). If we baked in class ids at ingestion time, toggling
    a class on/off would require re-ingesting the raw download. Instead,
    this step writes labels with the CANONICAL CLASS NAME as plain text
    (not a numeric id) so the final build_dataset.py step can assign ids
    fresh, every time, based on whatever is active right now.

Normalized label line format (NOT standard YOLO — intermediate only):
    <canonical_class_name> <cx> <cy> <w> <h>

Usage:
    python src/dataset/ingest_external.py \\
        --source-dir "data/external/Construction PPE.v3i.yolov8" \\
        --mapping configs/mappings/construction_ppe_skcet.yaml \\
        --out-dir data/normalized/construction-ppe-skcet
"""

import argparse
import shutil
from pathlib import Path

import yaml

SPLITS = ("train", "valid", "test")


def load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_source_class_names(source_dir: Path) -> list[str]:
    data_yaml = load_yaml(source_dir / "data.yaml")
    names = data_yaml["names"]
    if isinstance(names, dict):
        # some exports use {0: 'name', 1: 'name'} instead of a list
        names = [names[i] for i in range(len(names))]
    return names


def ingest_split(source_dir: Path, split: str, id_to_canonical: dict, out_dir: Path):
    img_dir = source_dir / split / "images"
    lbl_dir = source_dir / split / "labels"

    if not img_dir.exists():
        print(f"  [skip] no '{split}' split found at {img_dir}")
        return 0, 0

    out_img_dir = out_dir / split / "images"
    out_lbl_dir = out_dir / split / "labels"
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    n_images = 0
    n_boxes_kept = 0

    for img_path in sorted(img_dir.iterdir()):
        if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            continue

        label_path = lbl_dir / f"{img_path.stem}.txt"
        kept_lines = []

        if label_path.exists():
            with open(label_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    orig_id = int(parts[0])
                    coords = parts[1:]

                    canonical = id_to_canonical.get(orig_id)
                    if canonical is None:
                        continue  # dropped class (mapped to null, or unmapped id)

                    kept_lines.append(f"{canonical} {' '.join(coords)}")
                    n_boxes_kept += 1

        # Copy image regardless of whether it has kept boxes (could be a
        # legitimate background image). We prefix with source name to
        # avoid collisions if you ingest multiple external datasets later.
        source_tag = out_dir.name
        new_stem = f"{source_tag}_{img_path.stem}"
        shutil.copy2(img_path, out_img_dir / f"{new_stem}{img_path.suffix}")
        with open(out_lbl_dir / f"{new_stem}.txt", "w") as f:
            f.write("\n".join(kept_lines))

        n_images += 1

    return n_images, n_boxes_kept


def ingest(source_dir: Path, mapping_path: Path, out_dir: Path):
    mapping_cfg = load_yaml(mapping_path)
    name_mapping = mapping_cfg["mapping"]

    source_names = load_source_class_names(source_dir)
    print(f"Source classes ({len(source_names)}): {source_names}")

    # Build id -> canonical name lookup, skipping unmapped/null entries
    id_to_canonical = {}
    for idx, name in enumerate(source_names):
        if name not in name_mapping:
            print(f"  [WARN] class '{name}' (id {idx}) not found in mapping file — dropping it.")
            continue
        canonical = name_mapping[name]
        if canonical is not None:
            id_to_canonical[idx] = canonical

    print(f"Keeping {len(id_to_canonical)} of {len(source_names)} classes, "
          f"mapped to: {sorted(set(id_to_canonical.values()))}")

    if out_dir.exists():
        print(f"Removing existing normalized output at {out_dir}")
        shutil.rmtree(out_dir)

    totals = {"images": 0, "boxes": 0}
    for split in SPLITS:
        n_img, n_box = ingest_split(source_dir, split, id_to_canonical, out_dir)
        print(f"  {split}: {n_img} images, {n_box} boxes kept")
        totals["images"] += n_img
        totals["boxes"] += n_box

    print(f"Done. Total images: {totals['images']}, total boxes kept: {totals['boxes']}")
    print(f"Normalized output written to: {out_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest an external YOLO dataset into normalized form.")
    parser.add_argument("--source-dir", type=Path, required=True,
                         help="Path to the downloaded dataset root (contains train/valid/test + data.yaml)")
    parser.add_argument("--mapping", type=Path, required=True,
                         help="Path to the mapping yaml for this source dataset")
    parser.add_argument("--out-dir", type=Path, required=True,
                         help="Where to write normalized output, e.g. data/normalized/<source_name>")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingest(args.source_dir, args.mapping, args.out_dir)