"""
src/pipeline/process_image.py

Same idea as process_video.py but for a single image upload -- detect, match,
annotate, log, save output. Kept separate from process_video.py because the
"loop over frames" logic doesn't apply here, and forcing them into one
function would make both harder to read.
"""

import os
import cv2
from dataclasses import dataclass
from typing import List

from core.face_analyzer import FaceAnalyzer
from core.matcher import FaceMatcher
from db.postgres import get_session, RecognitionLog

COLOR_KNOWN = (255, 217, 0)
COLOR_UNKNOWN = (0, 0, 255)


@dataclass
class DetectionRecord:
    person_id: int | None
    person_name: str | None
    confidence: float
    status: str
    bbox: list  # [x1, y1, x2, y2]


@dataclass
class ProcessImageResult:
    output_path: str
    detections: List[DetectionRecord]


def process_image(
    image_path: str,
    output_path: str,
    source_label: str,
    confidence_threshold: float = 0.40,
    gpu: bool = True,
) -> ProcessImageResult:
    analyzer = FaceAnalyzer(gpu=gpu)
    matcher = FaceMatcher(threshold=confidence_threshold)

    image = cv2.imread(image_path)
    if image is None:
        raise RuntimeError(f"Could not read image: {image_path}")

    faces = analyzer.analyze(image)
    session = get_session()
    detections: List[DetectionRecord] = []

    try:
        for face in faces:
            result = matcher.match(face.normed_embedding)
            x1, y1, x2, y2 = face.bbox.astype(int)

            if result.is_known:
                label = f"{result.person_name} ({result.confidence:.2f})"
                color = COLOR_KNOWN
                status = "known"
            else:
                label = f"Unknown ({result.confidence:.2f})"
                color = COLOR_UNKNOWN
                status = "unknown"

            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(image, label, (x1, max(y1 - 10, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            log_entry = RecognitionLog(
                person_id=result.person_id,
                source=source_label,
                timestamp_in_video=None,
                confidence=result.confidence,
                status=status,
            )
            session.add(log_entry)

            detections.append(DetectionRecord(
                person_id=result.person_id,
                person_name=result.person_name,
                confidence=result.confidence,
                status=status,
                bbox=[int(x1), int(y1), int(x2), int(y2)],
            ))

        session.commit()
    finally:
        session.close()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, image)

    return ProcessImageResult(output_path=output_path, detections=detections)