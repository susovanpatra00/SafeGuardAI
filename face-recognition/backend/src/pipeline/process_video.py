"""
src/pipeline/process_video.py

Reads a video file frame by frame, runs face detection + matching on sampled
frames (not every single frame -- too slow, and consecutive frames are nearly
identical anyway), draws annotated boxes, writes an output video, and logs
every recognition event to Postgres.

Pipeline per sampled frame:
    Frame -> Face Detector -> [for each face] -> Embed -> Match (FAISS+Postgres)
        -> draw box + label -> log to recognition_logs table

NOTE: liveness/anti-spoof is deliberately NOT included yet (deferred per plan).
When we add it, it slots in right after detection, before matching -- see the
TODO comment below for exactly where.
"""

import os
import cv2
import time
from dataclasses import dataclass

from core.face_analyzer import FaceAnalyzer
from core.matcher import FaceMatcher
from db.postgres import get_session, RecognitionLog

# Colors in BGR (OpenCV format)
COLOR_KNOWN = (255, 217, 0)      # cyan-ish blue, matches the UI's "known" color
COLOR_UNKNOWN = (0, 0, 255)      # red, matches the UI's "unknown" color


@dataclass
class ProcessVideoResult:
    output_path: str
    total_frames_processed: int
    total_detections: int
    known_count: int
    unknown_count: int
    duration_seconds: float


def process_video(
    video_path: str,
    output_path: str,
    source_label: str,
    sample_every_n_frames: int = 5,
    confidence_threshold: float = 0.40,
    gpu: bool = True,
) -> ProcessVideoResult:
    """
    video_path: input video file (mp4/mov etc.)
    output_path: where to write the annotated output video
    source_label: human-readable source name for logging, e.g. "Cam-01 - Lobby"
                  or the uploaded filename.
    sample_every_n_frames: run detection every Nth frame. 1 = every frame (slow,
                  most accurate). 5-10 is a good default for near-real-time feel
                  without wasting compute on near-duplicate frames.
    confidence_threshold: passed to FaceMatcher -- similarity below this = "Unknown".
    """
    start_time = time.time()

    analyzer = FaceAnalyzer(gpu=gpu)
    matcher = FaceMatcher(threshold=confidence_threshold)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    session = get_session()

    frame_index = 0
    processed_count = 0
    total_detections = 0
    known_count = 0
    unknown_count = 0

    # cache the last annotated boxes so skipped frames still show something
    # reasonable rather than flickering blank -- keeps output video watchable.
    last_boxes = []  # list of (bbox, label, color)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_seconds = frame_index / fps

            if frame_index % sample_every_n_frames == 0:
                faces = analyzer.analyze(frame)
                last_boxes = []

                for face in faces:
                    total_detections += 1

                    # TODO(liveness): insert anti-spoof check here, e.g.:
                    #   if not liveness_checker.is_live(frame, face):
                    #       log status="spoof", draw amber box, `continue` to skip matching
                    # Deferred for now per plan -- matching runs on every detected face.

                    result = matcher.match(face.normed_embedding)

                    x1, y1, x2, y2 = face.bbox.astype(int)

                    if result.is_known:
                        known_count += 1
                        label = f"{result.person_name} ({result.confidence:.2f})"
                        color = COLOR_KNOWN
                        status = "known"
                    else:
                        unknown_count += 1
                        label = f"Unknown ({result.confidence:.2f})"
                        color = COLOR_UNKNOWN
                        status = "unknown"

                    last_boxes.append(((x1, y1, x2, y2), label, color))

                    log_entry = RecognitionLog(
                        person_id=result.person_id,
                        source=source_label,
                        timestamp_in_video=round(timestamp_seconds, 2),
                        confidence=result.confidence,
                        status=status,
                    )
                    session.add(log_entry)

                processed_count += 1

            # draw whatever boxes we currently have (fresh or cached from last sample)
            for (x1, y1, x2, y2), label, color in last_boxes:
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, max(y1 - 10, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            writer.write(frame)
            frame_index += 1

        session.commit()
    finally:
        cap.release()
        writer.release()
        session.close()

    duration = time.time() - start_time

    return ProcessVideoResult(
        output_path=output_path,
        total_frames_processed=processed_count,
        total_detections=total_detections,
        known_count=known_count,
        unknown_count=unknown_count,
        duration_seconds=round(duration, 2),
    )