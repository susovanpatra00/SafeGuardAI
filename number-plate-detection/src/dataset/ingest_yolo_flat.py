"""
Ingest a "flat" YOLO-format dataset — images + label .txt files sitting
directly in one or more subfolders (e.g. per-video folders), with a
classes.txt instead of a data.yaml, and no pre-existing train/valid/test
split. This is a different shape than Roboflow's export (handled by
ingest_external.py), hence a separate script.

Splits are done by shuffling all (image, label) pairs pooled across every
subfolder, rather than assigning whole subfolders to a single split —
frames here are already sparsely sampled (large frame-number gaps), so
adjacent-frame leakage risk is low and pooling keeps every video
represented in train/valid/test.

Usage:
    python -m src.dataset.ingest_yolo_flat \
        --source-dir "data/external/indian-vehicle-number-plate-yolo" \
        --mapping configs/mappings/indian_traffic_video_yolo.yaml \
        --out-dir data/normalized/indian-traffic-video-yolo \
        --train-frac 0.8 --valid-frac 0.1 --seed 0
"""

import argparse
import logging
import random
import shutil
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_classes_txt(source_dir: Path) -> list[str]:
    classes_file = source_dir / "classes.txt"
    with open(classes_file) as f:
        return [line.strip() for line in f if line.strip()]


def build_id_remap(source_names: list[str], class_map: dict, target_classes: list[str]) -> dict[int, int]:
    remap = {}
    for old_id, name in enumerate(source_names):
        if name not in class_map:
            logger.warning("Class '%s' not in mapping, its labels will be dropped", name)
            continue
        remap[old_id] = target_classes.index(class_map[name])
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
                continue
            lines_out.append(" ".join([str(id_remap[old_id])] + parts[1:]))

    if lines_out:
        dst_label.parent.mkdir(parents=True, exist_ok=True)
        with open(dst_label, "w") as f:
            f.write("\n".join(lines_out) + "\n")


def collect_pairs(source_dir: Path) -> list[tuple[Path, Path | None]]:
    """Find every image across all subfolders, paired with its label file if one exists."""
    pairs = []
    for img_path in sorted(source_dir.rglob("*")):
        if img_path.suffix.lower() not in IMAGE_EXTS:
            continue
        label_path = img_path.with_suffix(".txt")
        pairs.append((img_path, label_path if label_path.exists() else None))
    return pairs


def ingest(
    source_dir: str,
    mapping_path: str,
    out_dir: str,
    train_frac: float = 0.8,
    valid_frac: float = 0.1,
    seed: int = 0,
):
    source_dir = Path(source_dir)
    out_dir = Path(out_dir)
    mapping = load_yaml(Path(mapping_path))

    source_names = load_classes_txt(source_dir)
    id_remap = build_id_remap(source_names, mapping["class_map"], mapping["target_classes"])
    logger.info("Source classes: %s | id remap: %s", source_names, id_remap)

    pairs = collect_pairs(source_dir)
    logger.info("Found %d images total across all subfolders", len(pairs))
    n_with_labels = sum(1 for _, lbl in pairs if lbl is not None)
    logger.info("%d images have a matching label file, %d do not (background/negatives)", n_with_labels, len(pairs) - n_with_labels)

    random.Random(seed).shuffle(pairs)
    n = len(pairs)
    n_train = int(n * train_frac)
    n_valid = int(n * valid_frac)
    splits = {
        "train": pairs[:n_train],
        "valid": pairs[n_train:n_train + n_valid],
        "test": pairs[n_train + n_valid:],
    }

    counts = {}
    for split_name, split_pairs in splits.items():
        out_img_dir = out_dir / split_name / "images"
        out_lbl_dir = out_dir / split_name / "labels"
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_path, label_path in split_pairs:
            # prefix with parent folder name (vid-1, vid-2, ...) to avoid filename collisions
            # across videos (they all restart frame numbering from 0)
            dst_name = f"{img_path.parent.name}_{img_path.name}"
            shutil.copy2(img_path, out_img_dir / dst_name)

            if label_path is not None:
                dst_label_name = f"{img_path.parent.name}_{label_path.name}"
                remap_label_file(label_path, out_lbl_dir / dst_label_name, id_remap)

        counts[split_name] = len(split_pairs)
        logger.info("%s: %d images copied", split_name, len(split_pairs))

    unified_yaml = {
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(mapping["target_classes"]),
        "names": mapping["target_classes"],
    }
    with open(out_dir / "data.yaml", "w") as f:
        yaml.safe_dump(unified_yaml, f, sort_keys=False)

    logger.info("Done. Split counts: %s", counts)
    logger.info("Normalized dataset written to %s", out_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--valid-frac", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    ingest(args.source_dir, args.mapping, args.out_dir, args.train_frac, args.valid_frac, args.seed)


if __name__ == "__main__":
    main()
