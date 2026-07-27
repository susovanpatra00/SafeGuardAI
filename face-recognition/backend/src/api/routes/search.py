"""
src/api/routes/search.py

Search semantics (worth being explicit about): we don't store a unique
embedding/thumbnail per individual detection event, only one embedding per
ENROLLED person. So "search by face" means: identify which enrolled person
the uploaded photo matches, then return every place that person shows up in
recognition_logs. This is different from "search every raw frame across all
footage" -- that would require storing per-frame embeddings, which we don't
do yet. If that's ever needed, it's a bigger pipeline change, not a small add.
"""

import os
import shutil
import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from core.face_analyzer import FaceAnalyzer
from core.matcher import FaceMatcher
from db.postgres import get_session, RecognitionLog
from utils.image_io import read_image_respecting_exif
from api.schemas import SearchFaceResponse, SearchMatchItem

router = APIRouter(prefix="/search", tags=["search"])

UPLOAD_DIR = "data/uploads/search_queries"

_analyzer = FaceAnalyzer(gpu=True)


@router.post("/face", response_model=SearchFaceResponse)
async def search_by_face(
    photo: UploadFile = File(...),
    confidence_threshold: float = Form(0.40),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    photo_path = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{photo.filename}")
    with open(photo_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    image = read_image_respecting_exif(photo_path)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not read uploaded photo")

    faces = _analyzer.analyze(image)
    if not faces:
        raise HTTPException(status_code=400, detail="No face detected in the uploaded photo")

    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    matcher = FaceMatcher(threshold=confidence_threshold)
    result = matcher.match(face.normed_embedding)

    if not result.is_known:
        return SearchFaceResponse(matched=False, search_confidence=result.confidence, matches=[])

    session = get_session()
    try:
        logs = (
            session.query(RecognitionLog)
            .filter(RecognitionLog.person_id == result.person_id)
            .order_by(RecognitionLog.created_at.desc())
            .limit(200)
            .all()
        )
        matches = [
            SearchMatchItem(
                id=log.id,
                source=log.source,
                timestamp_in_video=log.timestamp_in_video,
                confidence=log.confidence,
                created_at=log.created_at,
            )
            for log in logs
        ]
    finally:
        session.close()

    return SearchFaceResponse(
        matched=True,
        person_id=result.person_id,
        person_name=result.person_name,
        search_confidence=result.confidence,
        matches=matches,
    )