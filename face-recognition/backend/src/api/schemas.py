"""
src/api/schemas.py

Pydantic models for request/response validation. Kept in one file since the
API surface is still small -- split into schemas/people.py, schemas/detect.py
etc. later if this grows unwieldy.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------- People ----------

class PersonResponse(BaseModel):
    id: int
    name: str
    employee_id: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    notes: Optional[str] = None
    photo_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EnrollResponse(BaseModel):
    person: PersonResponse
    det_score: float
    message: str = "Enrolled successfully"


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    employee_id: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    notes: Optional[str] = None


# ---------- Search ----------

class SearchMatchItem(BaseModel):
    id: int
    source: str
    timestamp_in_video: Optional[float]
    confidence: float  # the ORIGINAL recognition confidence from that log event
    created_at: datetime


class SearchFaceResponse(BaseModel):
    matched: bool
    person_id: Optional[int] = None
    person_name: Optional[str] = None
    search_confidence: float  # how well the uploaded photo matched the enrolled person
    matches: List[SearchMatchItem] = []


# ---------- Detect ----------

class DetectionItem(BaseModel):
    person_id: Optional[int]
    person_name: Optional[str]
    confidence: float
    status: str  # known | unknown
    bbox: List[int]  # [x1, y1, x2, y2]
    timestamp_in_video: Optional[float] = None  # null for image uploads


class DetectUploadResponse(BaseModel):
    media_type: str  # "image" | "video"
    output_path: str
    total_detections: int
    known_count: int
    unknown_count: int
    duration_seconds: float
    detections: List[DetectionItem]


# ---------- Logs ----------

class LogEntry(BaseModel):
    id: int
    person_id: Optional[int]
    person_name: Optional[str]
    source: str
    timestamp_in_video: Optional[float]
    confidence: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class LogsResponse(BaseModel):
    total: int
    events: List[LogEntry]


# ---------- Dashboard ----------

class DashboardStats(BaseModel):
    total_enrolled_faces: int
    recognitions_today: int
    unknown_faces_flagged_today: int
    active_sources_today: int