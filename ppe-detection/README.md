# PPE Kit Detection

# Reproduce the Data Pipeline
```
mkdir -p data/external
# Download the Roboflow dataset again (or copy the zip over from your Mac via scp — faster than re-downloading if it's already local)
# Unzip into: data/external/Construction PPE.v3i.yolov8/

python src/dataset/ingest_external.py \
  --source-dir "data/external/Construction PPE.v3i.yolov8" \
  --mapping configs/mappings/construction_ppe_skcet.yaml \
  --out-dir data/normalized/construction-ppe-skcet

python src/dataset/build_dataset.py --skip-empty
```