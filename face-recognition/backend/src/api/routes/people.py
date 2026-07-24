"""
src/api/routes/people.py
"""

import os
import shutil
import cv2
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List

from core.face_analyzer import FaceAnalyzer
from db.postgres import get_session, Person, Embedding
from db.faiss_index import FaceIndex
from api.schemas import PersonResponse, EnrollResponse

router = APIRouter(prefix="/people", tags=["people"])

UPLOAD_DIR = "data/enrolled"

# Loaded once at module import, reused across requests -- loading InsightFace
# per-request would add several seconds of latency to every call.
_analyzer = FaceAnalyzer(gpu=True)


@router.post("", response_model=EnrollResponse)
async def enroll_person(
    name: str = Form(...),
    employee_id: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    photo: UploadFile = File(...),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    photo_path = os.path.join(UPLOAD_DIR, f"{name.replace(' ', '_')}_{photo.filename}")

    with open(photo_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    image = cv2.imread(photo_path)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not read uploaded photo")

    faces = _analyzer.analyze(image)
    if not faces:
        raise HTTPException(status_code=400, detail="No face detected in uploaded photo")

    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    session = get_session()
    try:
        person = Person(
            name=name,
            employee_id=employee_id,
            role=role,
            department=department,
            notes=notes,
            photo_path=photo_path,
        )
        session.add(person)
        session.flush()

        embedding_row = Embedding(
            person_id=person.id,
            faiss_index_id=person.id,
            embedding=face.normed_embedding.tolist(),
            source_photo=photo_path,
        )
        session.add(embedding_row)

        face_index = FaceIndex()
        face_index.add(person.id, face.normed_embedding)
        face_index.save()

        session.commit()
        session.refresh(person)

        return EnrollResponse(person=PersonResponse.model_validate(person), det_score=float(face.det_score))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.get("", response_model=List[PersonResponse])
async def list_people(search: Optional[str] = None, department: Optional[str] = None):
    session = get_session()
    try:
        query = session.query(Person)
        if search:
            query = query.filter(Person.name.ilike(f"%{search}%"))
        if department:
            query = query.filter(Person.department == department)
        people = query.order_by(Person.created_at.desc()).all()
        return [PersonResponse.model_validate(p) for p in people]
    finally:
        session.close()


@router.delete("/{person_id}")
async def delete_person(person_id: int):
    session = get_session()
    try:
        person = session.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        face_index = FaceIndex()
        try:
            face_index.remove(person_id)
            face_index.save()
        except Exception:
            pass  # id may not exist in index anymore; don't block deletion on this

        session.delete(person)  # cascades to embeddings via ON DELETE CASCADE
        session.commit()
        return {"message": f"Deleted {person.name}"}
    finally:
        session.close()