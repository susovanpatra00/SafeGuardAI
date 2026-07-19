"""
Ingest an externally downloaded (Roboflow-format) dataset into the
unified data/normalized/ layout, remapping class names/ids per a
mapping YAML.

Mirrors the ingest_external.py pattern used in ppe-detection: read the
source data.yaml, build old-id -> new-id remap using class_map, rewrite
label files with the new ids, copy images across unchanged.

Usage:
    python -m src.dataset.ingest_external \
        --source-dir "data/external/Indian number plate.v1i.yolov8" \
        --mapping configs/mappings/indian_number_plate_roboflow.yaml \
        --out-dir data/normalized/indian-number-plate-roboflow
"""

import argparse
import logging
import shutil
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SPLITS = ["train", "valid", "test"]


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_source_class_names(source_dir: Path) -> list[str]:
    data_yaml = load_yaml(source_dir / "data.yaml")
    return data_yaml["names"]


def build_id_remap(source_names: list[str], class_map: dict, target_classes: list[str]) -> dict[int, int]:
    """old_class_id -> new_class_id, based on class_map + target_classes order."""
    remap = {}
    for old_id, name in enumerate(source_names):
        if name not in class_map:
            logger.warning("Class '%s' not in mapping, its labels will be dropped", name)
            continue
        target_name = class_map[name]
        new_id = target_classes.index(target_name)
        remap[old_id] = new_id
    return remap


def remap_label_file(src_label: Path, dst_label: Path, id_remap: dict[int, int]):
    lines_out = []
    with open(src_label) as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            old_id = int(parts[0])
            if old_id not in id_remap:
                continue  # class dropped (not in mapping)
            new_id = id_remap[old_id]
            lines_out.append(" ".join([str(new_id)] + parts[1:]))

    if lines_out:
        dst_label.parent.mkdir(parents=True, exist_ok=True)
        with open(dst_label, "w") as f:
            f.write("\n".join(lines_out) + "\n")
    # if a source image had zero valid boxes after remap, we simply don't
    # write a label file for it (still copy the image for background/negatives)


def ingest(source_dir: str, mapping_path: str, out_dir: str):
    source_dir = Path(source_dir)
    out_dir = Path(out_dir)
    mapping = load_yaml(Path(mapping_path))

    source_names = load_source_class_names(source_dir)
    id_remap = build_id_remap(source_names, mapping["class_map"], mapping["target_classes"])
    logger.info("Class id remap: %s", id_remap)

    counts = {}
    for split in SPLITS:
        split_img_dir = source_dir / split / "images"
        split_lbl_dir = source_dir / split / "labels"
        if not split_img_dir.exists():
            logger.info("No '%s' split found, skipping", split)
            continue

        out_img_dir = out_dir / split / "images"
        out_lbl_dir = out_dir / split / "labels"
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        n_images = 0
        for img_path in split_img_dir.glob("*.*"):
            shutil.copy2(img_path, out_img_dir / img_path.name)
            n_images += 1

            label_path = split_lbl_dir / (img_path.stem + ".txt")
            if label_path.exists():
                remap_label_file(label_path, out_lbl_dir / label_path.name, id_remap)

        counts[split] = n_images
        logger.info("%s: %d images copied", split, n_images)

    # write unified data.yaml for this normalized dataset
    unified_yaml = {
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(mapping["target_classes"]),
        "names": mapping["target_classes"],
    }
    with open(out_dir / "data.yaml", "w") as f:
        yaml.safe_dump(unified_yaml, f, sort_keys=False)

    logger.info("Done. Image counts per split: %s", counts)
    logger.info("Normalized dataset written to %s", out_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    ingest(args.source_dir, args.mapping, args.out_dir)


if __name__ == "__main__":
    main()
