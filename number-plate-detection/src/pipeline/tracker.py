"""
IOU-based tracker using globally-optimal (Hungarian algorithm) assignment.

Earlier version used greedy matching — each existing track grabbed the
best available detection in turn, first-come-first-served. In dense,
overlapping traffic this let an older track "steal" a detection that
actually belonged to a different nearby vehicle, silently carrying one
car's OCR history onto a different physical car (visible as the same
plate label appearing on two different vehicles). Hungarian assignment
finds the one-to-one pairing across all tracks and detections at once
that minimizes total mismatch, which avoids that failure mode.
"""

import itertools
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment


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
    ocr_history: list = field(default_factory=list)  # [(text, confidence), ...] — every
                                                        # accepted read, used for voting
                                                        # instead of trusting a single frame
    logged: bool = False


class PlateTracker:
    def __init__(self, iou_threshold: float = 0.3, max_missed_frames: int = 30):
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self.tracks: dict[int, Track] = {}
        self._id_counter = itertools.count(1)

    def update(self, detections: list[tuple[int, int, int, int]]) -> list[Track]:
        track_list = list(self.tracks.values())
        matched_det_indices: set[int] = set()

        if track_list and detections:
            cost_matrix = np.ones((len(track_list), len(detections)))
            for i, track in enumerate(track_list):
                for j, det in enumerate(detections):
                    cost_matrix[i, j] = 1.0 - iou(track.box, det)

            row_indices, col_indices = linear_sum_assignment(cost_matrix)

            matched_track_indices: set[int] = set()
            for r, c in zip(row_indices, col_indices):
                # cost <= 1 - iou_threshold means iou >= iou_threshold
                if cost_matrix[r, c] <= 1.0 - self.iou_threshold:
                    track = track_list[r]
                    track.box = detections[c]
                    track.frames_since_seen = 0
                    track.frames_since_ocr += 1
                    matched_track_indices.add(r)
                    matched_det_indices.add(c)

            for i, track in enumerate(track_list):
                if i not in matched_track_indices:
                    track.frames_since_seen += 1
        else:
            for track in track_list:
                track.frames_since_seen += 1

        unmatched_detections = [d for j, d in enumerate(detections) if j not in matched_det_indices]
        for det in unmatched_detections:
            new_id = next(self._id_counter)
            self.tracks[new_id] = Track(track_id=new_id, box=det, frames_since_ocr=999)

        self.tracks = {
            tid: t
            for tid, t in self.tracks.items()
            if t.frames_since_seen <= self.max_missed_frames
        }

        return list(self.tracks.values())