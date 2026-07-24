"""
src/api/routes/detect.py
"""

import os
import shutil
import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from pipeline.process_video import process_video
from pipeline.process_image import process_image
from api.schemas import DetectUploadResponse, DetectionItem

router = APIRouter(prefix="/detect", tags=["detect"])

UPLOAD_DIR = "data/uploads"
OUTPUT_DIR = "data/uploads/outputs"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@router.post("/upload", response_model=DetectUploadResponse)
async def detect_upload(
    file: UploadFile = File(...),
    confidence_threshold: float = Form(0.40),
    source_label: str = Form("Upload"),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()

    input_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    timestamp = int(time.time())

    if ext in IMAGE_EXTENSIONS:
        output_path = os.path.join(OUTPUT_DIR, f"{timestamp}_{file.filename}")
        result = process_image(
            image_path=input_path,
            output_path=output_path,
            source_label=source_label,
            confidence_threshold=confidence_threshold,
        )
        detections = [
            DetectionItem(
                person_id=d.person_id,
                person_name=d.person_name,
                confidence=d.confidence,
                status=d.status,
                bbox=d.bbox,
                timestamp_in_video=None,
            )
            for d in result.detections
        ]
        known = sum(1 for d in detections if d.status == "known")
        return DetectUploadResponse(
            media_type="image",
            output_path=result.output_path,
            total_detections=len(detections),
            known_count=known,
            unknown_count=len(detections) - known,
            duration_seconds=0.0,
            detections=detections,
        )

    elif ext in VIDEO_EXTENSIONS:
        output_path = os.path.join(OUTPUT_DIR, f"{timestamp}_{file.filename}")
        result = process_video(
            video_path=input_path,
            output_path=output_path,
            source_label=source_label,
            confidence_threshold=confidence_threshold,
        )
        # NOTE: process_video logs to the DB but doesn't currently return per-detection
        # bbox details (only aggregate counts) -- the UI's Detections table can be
        # populated from GET /logs filtered by source_label instead. Revisit if we
        # want bbox-level detail returned directly from this endpoint too.
        return DetectUploadResponse(
            media_type="video",
            output_path=result.output_path,
            total_detections=result.total_detections,
            known_count=result.known_count,
            unknown_count=result.unknown_count,
            duration_seconds=result.duration_seconds,
            detections=[],
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")