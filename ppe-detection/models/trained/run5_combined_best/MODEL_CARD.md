# Model: run5_combined_best

## Summary
YOLO11s trained on 3 combined datasets for PPE compliance detection
(person, helmet, vest, boots — plus bonus gloves/goggles/negative
classes not used in compliance logic).

## Training data
- `construction-ppe-skcet` (Roboflow, ~8,845 images) — large volume, mixed quality
- `ketakichalke` / Ultralytics Construction-PPE (~1,416 images) — curated, clean
- `SH17` (~8,099 images) — diverse industrial scenes, CC BY-NC-SA 4.0 (non-commercial —
  used for demo purposes only per project decision; do not use in a shipped
  commercial product without revisiting the license)

Combined merged dataset: 17,507 images, 76,902 boxes, 11 classes.

## Validation results (143-2,482 image val set, imgsz=768)
| Class  | Precision | Recall | mAP50 | mAP50-95 |
|--------|-----------|--------|-------|----------|
| person | 0.825     | 0.895  | 0.896 | 0.705    |
| helmet | 0.869     | 0.908  | 0.911 | 0.678    |
| vest   | 0.890     | 0.899  | 0.929 | 0.730    |
| boots  | 0.830     | 0.797  | 0.838 | 0.587    |

(gloves/goggles/negative classes scored lower — not used in compliance
logic, see data/active_classes.yaml)

## Known limitations
- SH17 contains a meaningful fraction of non-industrial stock photos
  (offices, medical settings, etc.) — model correctly identifies these
  as "non-compliant" (no PPE visible) but this isn't a construction-
  relevant test case.
- Tight upper-body/portrait crops (vs full-body shots) are underrepresented
  in training data — person detection may be less reliable on these framings.
- Trained and validated on curated datasets, not on the client's actual
  camera footage — real-world performance on deployment footage should
  be validated separately before production use.

## Training config
- Model: yolo11s.pt
- imgsz: 768, batch: auto, epochs: 81 (early-stopped, patience=15, best at epoch 66)
- Hardware: NVIDIA A100-PCIE-40GB