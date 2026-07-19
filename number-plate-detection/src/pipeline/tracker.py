"""
Minimal IOU-based tracker.

Not trying to be DeepSORT here — plates don't need appearance embeddings,
they just need "is this the same box I saw a few frames ago" so we can
(a) avoid re-OCRing every frame and (b) avoid logging the same plate
100 times as a car sits in frame.
"""

import itertools
from dataclasses import dataclass, field


def iou(box_a, box_b) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0

    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


@dataclass
class Track:
    track_id: int
    box: tuple[int, int, int, int]
    frames_since_seen: int = 0
    frames_since_ocr: int = 0
    best_text: str | None = None
    best_confidence: float = 0.0
    logged: bool = False


class PlateTracker:
    def __init__(self, iou_threshold: float = 0.3, max_missed_frames: int = 30):
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self.tracks: dict[int, Track] = {}
        self._id_counter = itertools.count(1)

    def update(self, detections: list[tuple[int, int, int, int]]) -> list[Track]:
        unmatched_detections = list(detections)
        matched_track_ids = set()

        for track in self.tracks.values():
            best_match, best_iou = None, self.iou_threshold
            for det in unmatched_detections:
                score = iou(track.box, det)
                if score > best_iou:
                    best_match, best_iou = det, score

            if best_match is not None:
                track.box = best_match
                track.frames_since_seen = 0
                track.frames_since_ocr += 1
                matched_track_ids.add(track.track_id)
                unmatched_detections.remove(best_match)
            else:
                track.frames_since_seen += 1

        for det in unmatched_detections:
            new_id = next(self._id_counter)
            self.tracks[new_id] = Track(track_id=new_id, box=det, frames_since_ocr=999)

        self.tracks = {
            tid: t
            for tid, t in self.tracks.items()
            if t.frames_since_seen <= self.max_missed_frames
        }

        return list(self.tracks.values())
