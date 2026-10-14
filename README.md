# SafeGuardAI

Computer vision for site safety. Four separate modules, each one takes a camera feed or an image and flags something a person would otherwise have to keep an eye on: who is in the frame, whether there is fire or smoke, which vehicle just came in, and whether workers are wearing their PPE.

Every module lives in its own folder with its own setup and they don't depend on each other.

| Module | What it does | Built with |
|---|---|---|
| `face-recognition` | Enroll people, search by face, run detection on images and video | InsightFace, FAISS, Postgres, FastAPI, React |
| `fire_smoke_detection` | Detects fire and smoke | YOLO11 |
| `number-plate-detection` | Reads Indian number plates from an RTSP camera | YOLO, PaddleOCR |
| `ppe-detection` | Checks each worker for helmet, vest and boots and marks them compliant or not | YOLO11s |

## face-recognition

InsightFace (buffalo_l) turns each face into a 512-d ArcFace embedding. Embeddings are searched with an exact FAISS cosine index, and the people they belong to are stored in Postgres.

The match threshold is 0.40. On the test images, the same person scored about 0.70 and different people scored between -0.04 and 0.03, so 0.40 sits in the gap. It needs retuning on real camera footage, since lighting and angle move that gap.

The FastAPI backend has endpoints to enroll and delete people, search by face, upload an image or video for detection, and pull logs and dashboard stats. The frontend is a React (TanStack Start) dashboard with pages for enrolling, searching, upload detection and logs.

```bash
# backend
cd face-recognition/backend
uv sync
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# frontend
cd face-recognition/frontend
npm i
npm run dev
```

Postgres has to be running with the tables from `configs/schema.sql`. Connection settings are in `configs/db.yaml`. The frontend talks to `http://localhost:8000` unless you set `VITE_API_BASE_URL`.

Not done yet: liveness check, the background job worker, and live camera detection. CORS is wide open for local development, so tighten it before putting this anywhere public.

## fire_smoke_detection

A YOLO11 model with two classes, `smoke` and `fire`. Datasets from different places (D-Fire, Roboflow, your own labelled data) each get a small mapping file that renames their classes to the same two names. They are then merged into one training set and trained with a single script. Adding a new data source means adding one mapping file.

Setup, data download and training steps are in `fire_smoke_detection/README.md`.

## number-plate-detection

Reads Indian number plates from a live RTSP feed.

RTSP frame, YOLO plate detector, IOU tracker (so the same plate isn't OCR'd on every frame), PaddleOCR, regex check for the Indian plate format, then a CSV log and a cropped image of the plate.

The detector is trained on 548 images of Indian plates from a Roboflow dataset (CC BY 4.0). OCR is the expensive step, so `frame_skip` and `ocr_interval_frames` in the config are the two knobs for GPU load. The tracker is a plain IOU matcher, not DeepSORT. Plates don't need appearance matching within one camera's short view of a car.

## ppe-detection

Detects person, helmet, vest and boots, matches each PPE item to the right person, and marks that person COMPLIANT or NON-COMPLIANT based on what is missing.

Trained on 17,507 images (76,902 boxes) merged from three datasets: a large Roboflow construction PPE set, the Ultralytics Construction-PPE set, and SH17. YOLO11s at 768px on an A100. Early stopping ended it at epoch 81 and the best weights are from epoch 66.

| Class | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| person | 0.825 | 0.895 | 0.896 | 0.705 |
| helmet | 0.869 | 0.908 | 0.911 | 0.678 |
| vest | 0.890 | 0.899 | 0.929 | 0.730 |
| boots | 0.830 | 0.797 | 0.838 | 0.587 |

Gloves, goggles and the `no_*` classes score lower and aren't used in the compliance check.

Limits worth knowing:
- This was validated on public datasets, not on footage from a real site camera. Test it on your own cameras before relying on it.
- SH17 has a fair number of non-industrial stock photos (offices, clinics). The model correctly calls those non-compliant, but they aren't a useful construction test.
- Tight upper-body crops are underrepresented in the training data, so person detection is weaker on them.

The model card is at `ppe-detection/models/trained/run5_combined_best/MODEL_CARD.md`.

## Licensing

SH17 is CC BY-NC-SA 4.0, so the PPE weights trained on it are for non-commercial use only. Check the dataset licenses before shipping any of these models in a product.
