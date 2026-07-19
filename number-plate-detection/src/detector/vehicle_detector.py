"""
Stage 1 of the cascade: detect vehicles using plain pretrained YOLO
(COCO classes already include car/motorcycle/bus/truck — no fine-tuning
needed here). Vehicles are large, easy targets even in wide/distant
camera shots, unlike plates.
"""

import logging

import numpy as np
from ultralytics import YOLO

from src.detector.plate_detector import Detection

logger = logging.getLogger(__name__)

COCO_VEHICLE_CLASS_NAMES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


class VehicleDetector:
    def __init__(
        self,
        weights_path: str = "yolov8n.pt",
        conf_threshold: float = 0.4,
        iou_threshold: float = 0.5,
        device: str = "cuda:0",
        classes: list[int] | None = None,
    ):
        logger.info("Loading vehicle detector weights from %s", weights_path)
        self.model = YOLO(weights_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.classes = classes or list(COCO_VEHICLE_CLASS_NAMES.keys())

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            classes=self.classes,
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
