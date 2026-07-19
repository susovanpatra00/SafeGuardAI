"""
YOLO wrapper for license plate localization.

Trains/loads a single-class ("plate") YOLO model — you fine-tune this
the same way you did ppe-detection: grab a Roboflow license-plate dataset,
run it through src/dataset/ingest_external.py, then `yolo train`.
"""

import logging
from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    box: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float


class PlateDetector:
    def __init__(
        self,
        weights_path: str,
        conf_threshold: float = 0.45,
        iou_threshold: float = 0.5,
        device: str = "cuda:0",
    ):
        logger.info("Loading plate detector weights from %s", weights_path)
        self.model = YOLO(weights_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )[0]

        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            detections.append(
                Detection(box=(int(x1), int(y1), int(x2), int(y2)), confidence=conf)
            )
        return detections

    @staticmethod
    def crop(frame: np.ndarray, detection: Detection, pad: int = 4) -> np.ndarray:
        x1, y1, x2, y2 = detection.box
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
        return frame[y1:y2, x1:x2]
